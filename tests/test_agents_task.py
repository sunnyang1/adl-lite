"""M2 task-layer tests: status derivation, rework loop, invalid transitions,
chain integrity, result_ref, dual-state semantics, discovery isolation.
"""

from __future__ import annotations

import pytest

from adl_lite import chain_kind
from adl_lite.agents.bus import TaskQueue
from adl_lite.agents.task import (
    _TASK_TRANSITIONS,
    TaskRegistry,
    TaskStatus,
    TaskStatusView,
    derive_task_status,
)
from adl_lite.exceptions import ADLConsensusError
from adl_lite.models import Event, EventChain, EventType


def _chain(events: list[tuple[EventType, dict]]) -> EventChain:
    c = EventChain(concept_id="t:test")
    for i, (et, payload) in enumerate(events):
        c.append(Event(concept_id="t:test", event_type=et, actor=f"a{i}", payload=payload))
    return c


def _full_chain() -> EventChain:
    """create -> claim -> submit -> validate(accept) -> close"""
    return _chain(
        [
            (EventType.TASK_CREATE, {"objective": "x"}),
            (EventType.TASK_CLAIM, {}),
            (EventType.TASK_SUBMIT, {"result_ref": "cap-1"}),
            (EventType.TASK_VALIDATE, {"accepted": True}),
            (EventType.TASK_CLOSE, {"outcome": "accepted"}),
        ]
    )


class TestDerivation:
    def test_transition_table_shape(self) -> None:
        """TS-01: every status appears exactly once as a key."""
        assert set(_TASK_TRANSITIONS) == set(TaskStatus)

    @pytest.mark.parametrize(
        ("events", "expected"),
        [
            ([(EventType.TASK_CREATE, {})], TaskStatus.OPEN),
            ([(EventType.TASK_CREATE, {}), (EventType.TASK_ASSIGN, {})], TaskStatus.ASSIGNED),
            ([(EventType.TASK_CREATE, {}), (EventType.TASK_CLAIM, {})], TaskStatus.IN_PROGRESS),
            (
                [
                    (EventType.TASK_CREATE, {}),
                    (EventType.TASK_CLAIM, {}),
                    (EventType.TASK_SUBMIT, {}),
                ],
                TaskStatus.SUBMITTED,
            ),
            (
                [
                    (EventType.TASK_CREATE, {}),
                    (EventType.TASK_CLAIM, {}),
                    (EventType.TASK_SUBMIT, {}),
                    (EventType.TASK_VALIDATE, {"accepted": True}),
                ],
                TaskStatus.VALIDATED,
            ),
            (
                [
                    (EventType.TASK_CREATE, {}),
                    (EventType.TASK_CLAIM, {}),
                    (EventType.TASK_SUBMIT, {}),
                    (EventType.TASK_VALIDATE, {"accepted": False}),
                ],
                TaskStatus.REJECTED,
            ),
            (
                [(EventType.TASK_CREATE, {}), (EventType.TASK_CLOSE, {"outcome": "cancelled"})],
                TaskStatus.CLOSED,
            ),
        ],
    )
    def test_derivation_paths(self, events, expected) -> None:
        """TS-01: each transition path derives the expected status."""
        assert derive_task_status(_chain(events).events) == expected

    def test_rework_loop(self) -> None:
        """TS-02: submit -> reject -> submit -> accept -> close."""
        chain = _chain(
            [
                (EventType.TASK_CREATE, {}),
                (EventType.TASK_CLAIM, {}),
                (EventType.TASK_SUBMIT, {"result_ref": "cap-a"}),
                (EventType.TASK_VALIDATE, {"accepted": False}),
                (EventType.TASK_CLAIM, {}),
                (EventType.TASK_SUBMIT, {"result_ref": "cap-b"}),
                (EventType.TASK_VALIDATE, {"accepted": True}),
                (EventType.TASK_CLOSE, {"outcome": "accepted"}),
            ]
        )
        statuses = [derive_task_status(chain.events[: i + 1]) for i in range(len(chain.events))]
        assert statuses == [
            TaskStatus.OPEN,
            TaskStatus.IN_PROGRESS,
            TaskStatus.SUBMITTED,
            TaskStatus.REJECTED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.SUBMITTED,
            TaskStatus.VALIDATED,
            TaskStatus.CLOSED,
        ]


class TestTaskStatusView:
    def test_result_ref(self) -> None:
        """TS-05/P1-5: TaskStatusView.result_ref returns the latest submission."""
        view = TaskStatusView(_full_chain())
        assert view.result_ref == "cap-1"

    def test_validators_distinct(self) -> None:
        chain = _chain(
            [
                (EventType.TASK_CREATE, {}),
                (EventType.TASK_CLAIM, {}),
                (EventType.TASK_SUBMIT, {}),
                (EventType.TASK_VALIDATE, {"accepted": True}),
                (EventType.TASK_VALIDATE, {"accepted": True}),
            ]
        )
        assert TaskStatusView(chain).validators == ["a3", "a4"]  # distinct actors


class TestRegistry:
    def test_lifecycle_via_registry(self) -> None:
        """Full create->claim->submit->validate->close through the registry."""
        reg = TaskRegistry()
        task = reg.create_task("do x", required_capabilities=["depends-on"])
        assert chain_kind(reg.engine.chains[task.task_id]) == "task"
        assert reg.engine.chains[task.task_id].verify_integrity() is True  # TS-04
        reg.claim(task.task_id, "agent-1")
        reg.submit(task.task_id, "agent-1", "cap-result")
        reg.validate_result(task.task_id, "agent-2", accepted=True)
        reg.close(task.task_id, "supervisor", "accepted")
        got = reg.get_task(task.task_id)
        assert got.status == TaskStatus.CLOSED
        assert got.result_ref == "cap-result"

    def test_invalid_transition_rejected(self) -> None:
        """TS-03: submit from OPEN (no claim) is rejected; no event appended."""
        reg = TaskRegistry()
        task = reg.create_task("x")
        with pytest.raises(ADLConsensusError, match="invalid task transition"):
            reg.submit(task.task_id, "a1", "cap-1")
        assert reg.derive_task_status(reg.engine.chains[task.task_id]) == TaskStatus.OPEN

    def test_rework_via_registry(self) -> None:
        reg = TaskRegistry()
        task = reg.create_task("x")
        reg.claim(task.task_id, "a1")
        reg.submit(task.task_id, "a1", "cap-1")
        reg.validate_result(task.task_id, "a2", accepted=False)
        assert reg.get_task(task.task_id).status == TaskStatus.REJECTED
        reg.claim(task.task_id, "a1")  # rework re-entry
        reg.submit(task.task_id, "a1", "cap-2")
        reg.validate_result(task.task_id, "a2", accepted=True)
        reg.close(task.task_id, "sup", "accepted")
        assert reg.get_task(task.task_id).status == TaskStatus.CLOSED

    def test_dual_state_restart(self) -> None:
        """TS-06: a NEW TaskQueue loses leases, but chain result state survives."""
        reg = TaskRegistry()
        task = reg.create_task("x")
        reg.claim(task.task_id, "a1")
        reg.submit(task.task_id, "a1", "cap-1")

        q1 = TaskQueue(reg)
        assert q1.claim(task.task_id, "a1") is True  # a1 holds the runtime lease

        # "Process restart": fresh queue over the same engine.
        q2 = TaskQueue(reg)
        assert q2.claim(task.task_id, "b1") is True  # lease was volatile
        assert reg.get_task(task.task_id).status == TaskStatus.SUBMITTED  # truth intact

    def test_list_tasks_filters_status(self) -> None:
        reg = TaskRegistry()
        t1 = reg.create_task("x")
        t2 = reg.create_task("y")
        reg.claim(t2.task_id, "a1")
        open_tasks = reg.list_tasks(status=TaskStatus.OPEN)
        assert [t.task_id for t in open_tasks] == [t1.task_id]
        assert all(t.status == TaskStatus.OPEN for t in open_tasks)

    def test_task_chain_integrity(self) -> None:
        """TS-04 companion: full lifecycle chain passes verify_integrity."""
        chain = _full_chain()
        assert chain.verify_integrity() is True

    def test_discovery_isolation(self) -> None:
        """TS-08: task chains stay out of discovery views (P0-2)."""
        reg = TaskRegistry()
        task = reg.create_task("x")
        from adl_lite.agents.identity import chain_kind as ck

        assert ck(reg.engine.chains[task.task_id]) == "task"
        assert reg.engine.chains[task.task_id].status.value == "provisional"
