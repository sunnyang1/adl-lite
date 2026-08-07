"""Task lifecycle as EventChains (M2).

Dual-state semantics (first-principles): RESULT state (SUBMITTED/VALIDATED/
CLOSED...) is DERIVED from the chain and is the only source of truth; claim
leases and runtime state are volatile caches owned by ``agents.bus.TaskQueue``
and are intentionally NOT chain-backed (a lease is a process, not a fact).

Capability vocabulary (P1-3): ``required_capabilities`` values must come from
the ontology predicate set OR registered discovery chain ids — matching the
vocabulary used by agent.capabilities and TaskQueue.dequeue.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..consensus import ConsensusEngine
from ..exceptions import ADLConsensusError
from ..models import Event, EventChain, EventType
from ..ontology import default_ontology
from .identity import chain_kind


class TaskStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    REJECTED = "rejected"
    CLOSED = "closed"


_TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.OPEN: {TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS, TaskStatus.CLOSED},
    TaskStatus.ASSIGNED: {TaskStatus.IN_PROGRESS},
    # IN_PROGRESS -> IN_PROGRESS is an IDEMPOTENT re-claim: when a runtime
    # execution fails (or a human checkpoint rejects), the chain keeps the
    # earlier TASK_CLAIM and the lease is released back to the queue; the next
    # dequeue re-claims the same task to retry (M3 recovery semantics).
    TaskStatus.IN_PROGRESS: {TaskStatus.IN_PROGRESS, TaskStatus.SUBMITTED},
    TaskStatus.SUBMITTED: {TaskStatus.VALIDATED, TaskStatus.REJECTED},
    TaskStatus.REJECTED: {TaskStatus.IN_PROGRESS, TaskStatus.CLOSED},  # rework loop
    TaskStatus.VALIDATED: {TaskStatus.CLOSED},
    TaskStatus.CLOSED: set(),
}


def _event_to_status(et: EventType, payload: dict[str, Any]) -> TaskStatus | None:
    """Map a task event to the resulting status (None = no status change)."""
    if et == EventType.TASK_CREATE:
        return TaskStatus.OPEN
    if et == EventType.TASK_ASSIGN:
        return TaskStatus.ASSIGNED
    if et == EventType.TASK_CLAIM:
        return TaskStatus.IN_PROGRESS
    if et == EventType.TASK_SUBMIT:
        return TaskStatus.SUBMITTED
    if et == EventType.TASK_VALIDATE:
        return TaskStatus.VALIDATED if payload.get("accepted") else TaskStatus.REJECTED
    if et == EventType.TASK_CLOSE:
        return TaskStatus.CLOSED
    return None


def derive_task_status(events: Iterable[Event]) -> TaskStatus:
    """Deterministic ordered fold (not a pure LUB — rework needs REJECTED →
    SUBMITTED re-entry). O(n), result state only."""
    status = TaskStatus.OPEN
    for e in events:
        s = _event_to_status(e.event_type, e.payload)
        if s is not None:
            status = s
    return status


class TaskStatusView:
    """Cached result-status derivation over a task chain (chain itself
    untouched). Cache is invalidated by the tail hash."""

    def __init__(self, chain: EventChain) -> None:
        self._chain = chain
        self._key: str | None = None
        self._status = TaskStatus.OPEN

    @property
    def status(self) -> TaskStatus:
        key = self._chain.events[-1].hash if self._chain.events else ""
        if key != self._key:
            self._status = derive_task_status(self._chain.events)
            self._key = key
        return self._status

    @property
    def validators(self) -> list[str]:
        seen: list[str] = []
        for e in self._chain.events:
            if e.event_type == EventType.TASK_VALIDATE and e.actor not in seen:
                seen.append(e.actor)
        return seen

    @property
    def result_ref(self) -> str | None:
        """Latest TASK_SUBMIT result reference (P1-5)."""
        ref: str | None = None
        for e in self._chain.events:
            if e.event_type == EventType.TASK_SUBMIT:
                ref = e.payload.get("result_ref")
        return ref


class Task(BaseModel):
    """Task view. ``status`` is a snapshot; the authoritative value is
    ``derive_task_status`` over the chain. ``lease_until`` is a volatile
    runtime snapshot — never a source of truth."""

    task_id: str
    objective: str
    required_capabilities: list[str] = Field(default_factory=list)
    assigned_to: str | None = None
    status: TaskStatus = TaskStatus.OPEN
    result_ref: str | None = None
    parent_task_id: str | None = None
    created_by: str = "planner"
    tenant: str | None = None
    scope: str = "public"
    priority: int = 0
    lease_until: str | None = None


class TaskRegistry:
    """Task lifecycle over a ConsensusEngine.

    Capability vocabulary (P1-3): required_capabilities must be ontology
    predicates or registered discovery chain ids — the SAME vocabulary used by
    agent.capabilities and TaskQueue.dequeue, so planner validation and queue
    matching never diverge.
    """

    def __init__(self, engine: ConsensusEngine | None = None) -> None:
        self.engine = engine or ConsensusEngine(dev_mode=True)

    # ------------------------------------------------------------------
    # Vocabulary (P1-3)
    # ------------------------------------------------------------------

    def _is_known_capability(self, capability: str) -> bool:
        om = default_ontology()
        if om.validate_predicate(capability):
            return True
        return any(
            chain_kind(self.engine.chains[c]) == "discovery" and c == capability
            for c in self.engine.chains
        )

    def known_capabilities(self) -> list[str]:
        om = default_ontology()
        caps = set(om.list_predicates())
        caps.update(
            c for c in self.engine.chains if chain_kind(self.engine.chains[c]) == "discovery"
        )
        return sorted(caps)

    # ------------------------------------------------------------------
    # Lifecycle (all events appended to chain `task:<uuid>`)
    # ------------------------------------------------------------------

    def create_task(
        self,
        objective: str,
        required_capabilities: list[str] | None = None,
        created_by: str = "planner",
        parent_task_id: str | None = None,
        priority: int = 0,
        scope: str = "public",
        tenant: str | None = None,
        input_ref: str | None = None,
        db_ref: str | None = None,
    ) -> Task:
        task_id = f"task:{uuid.uuid4().hex}"  # namespace: never collides with discovery ids
        genesis = Event(
            concept_id=task_id,
            event_type=EventType.TASK_CREATE,
            actor=created_by,
            payload={
                "objective": objective,
                "required_capabilities": required_capabilities or [],
                "parent_task_id": parent_task_id,
                "priority": priority,
                "scope": scope,
                "tenant": tenant,
                "input_ref": input_ref,
                "db_ref": db_ref,
            },
        )
        chain = EventChain(concept_id=task_id)
        chain.append(genesis)
        self.engine.chains[task_id] = chain
        return Task(
            task_id=task_id,
            objective=objective,
            required_capabilities=required_capabilities or [],
            parent_task_id=parent_task_id,
            priority=priority,
            scope=scope,
            tenant=tenant,
        )

    def assign(self, task_id: str, agent_did: str, actor: str) -> Event:
        self._guard_transition(task_id, TaskStatus.ASSIGNED)
        return self._append(task_id, EventType.TASK_ASSIGN, actor, {"agent_did": agent_did})

    def claim(self, task_id: str, agent_did: str) -> Event:
        """Claim only appends the chain event; lease atomicity lives in
        TaskQueue (volatile runtime state). IDEMPOTENT: re-claiming a task
        already IN_PROGRESS is legal (execution-retry recovery, M3); the
        queue lease is what enforces at-most-one among live workers."""
        self._guard_transition(task_id, TaskStatus.IN_PROGRESS)
        return self._append(task_id, EventType.TASK_CLAIM, agent_did, {"agent_did": agent_did})

    def submit(
        self,
        task_id: str,
        agent_did: str,
        result_ref: str,
        summary: str = "",
        confidence: float = 0.5,
    ) -> Event:
        """``result_ref`` = adl_id of the produced capability chain (should be
        registered via engine.register first)."""
        self._guard_transition(task_id, TaskStatus.SUBMITTED)
        return self._append(
            task_id,
            EventType.TASK_SUBMIT,
            agent_did,
            {"result_ref": result_ref, "summary": summary, "confidence": confidence},
        )

    def validate_result(
        self,
        task_id: str,
        validator_actor: str,
        accepted: bool,
        confidence: float = 0.8,
        critique: str = "",
    ) -> Event:
        """Accept/reject a submission (drives SUBMITTED→VALIDATED/REJECTED)."""
        target = TaskStatus.VALIDATED if accepted else TaskStatus.REJECTED
        self._guard_transition(task_id, target)
        return self._append(
            task_id,
            EventType.TASK_VALIDATE,
            validator_actor,
            {"accepted": accepted, "confidence": confidence, "critique": critique},
        )

    def close(
        self,
        task_id: str,
        actor: str,
        outcome: Literal["accepted", "rejected", "cancelled"],
        reason: str = "",
    ) -> Event:
        self._guard_transition(task_id, TaskStatus.CLOSED)
        return self._append(
            task_id, EventType.TASK_CLOSE, actor, {"outcome": outcome, "reason": reason}
        )

    # ------------------------------------------------------------------
    # Derived queries
    # ------------------------------------------------------------------

    def get_task(self, task_id: str) -> Task:
        chain = self.engine.chains[task_id]
        view = TaskStatusView(chain)
        genesis = chain.events[0].payload
        return Task(
            task_id=task_id,
            objective=genesis.get("objective", ""),
            required_capabilities=genesis.get("required_capabilities", []),
            status=view.status,
            result_ref=view.result_ref,
            parent_task_id=genesis.get("parent_task_id"),
            created_by=chain.events[0].actor,
            tenant=genesis.get("tenant"),
            scope=genesis.get("scope", "public"),
            priority=genesis.get("priority", 0),
        )

    def list_tasks(self, status: TaskStatus | None = None, tenant: str | None = None) -> list[Task]:
        out: list[Task] = []
        for cid, chain in self.engine.chains.items():
            if chain_kind(chain) != "task":
                continue
            t = self.get_task(cid)
            if status and t.status != status:
                continue
            if tenant and t.tenant != tenant:
                continue
            out.append(t)
        return sorted(out, key=lambda t: (-t.priority, t.task_id))

    def derive_task_status(self, chain: EventChain) -> TaskStatus:
        return derive_task_status(chain.events)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _append(self, task_id: str, et: EventType, actor: str, payload: dict[str, Any]) -> Event:
        event = Event(concept_id=task_id, event_type=et, actor=actor, payload=payload)
        self.engine.chains[task_id].append(event)
        return event

    def _guard_transition(self, task_id: str, to: TaskStatus) -> None:
        """Reject transitions not allowed by _TASK_TRANSITIONS from the
        CURRENT derived status. Rejected transitions never append events."""
        chain = self.engine.chains.get(task_id)
        if chain is None:
            raise ADLConsensusError(f"unknown task: {task_id}")
        current = derive_task_status(chain.events)
        if to not in _TASK_TRANSITIONS[current]:
            raise ADLConsensusError(f"invalid task transition {current.value} -> {to.value}")
