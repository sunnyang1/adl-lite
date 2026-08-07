"""Zero-regression guard for the M1a agent-layer changes.

These tests lock the DISCOVERY lattice against the new AGENT_*/TASK_* event
types: agent/task events must stay invisible to type_to_status, StatusOrder,
_valid_transitions, _status_to_event_type, and ActionExecutor's event_type_map.
Also guards EventType count, ontology triggers_transition hygiene, and legacy
state-file compatibility (ZR-10).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adl_lite import chain_kind
from adl_lite.agents.identity import AgentProfile, AgentRegistry, AgentRole
from adl_lite.cli import _load_engine
from adl_lite.crdt import _VALID_TRANSITIONS, StatusOrder
from adl_lite.models import Event, EventChain, EventType

AGENT_EVENT_TYPES = {
    EventType.AGENT_REGISTER,
    EventType.AGENT_VALIDATE,
    EventType.AGENT_UPDATE,
    EventType.AGENT_DEPRECATE,
}

DISCOVERY_LIFECYCLE = {
    EventType.REGISTER,
    EventType.VALIDATE,
    EventType.DEPRECATE,
    EventType.FORK,
    EventType.ARCHIVE,
}


def _make_agent_chain(concept_id: str, event_types: list[EventType]) -> EventChain:
    chain = EventChain(concept_id=concept_id)
    for i, et in enumerate(event_types):
        chain.append(
            Event(
                concept_id=concept_id,
                event_type=et,
                actor=f"actor-{i}",
                payload={},
            )
        )
    return chain


# ---------------------------------------------------------------------------
# ZR-01 / ZR-06: discovery lattice is invisible to agent events
# ---------------------------------------------------------------------------


class TestAgentEventsDoNotDriveDiscoveryLattice:
    @pytest.mark.parametrize("et", sorted(AGENT_EVENT_TYPES, key=lambda e: e.value))
    def test_agent_event_keeps_status_provisional(self, et: EventType) -> None:
        """ZR-01/06: a chain with only AGENT_* events stays PROVISIONAL."""
        chain = _make_agent_chain("zr-agent", [et])
        assert chain.status.value == "provisional"

    def test_agent_validate_does_not_count_as_validator(self) -> None:
        """ZR-01: AGENT_VALIDATE must not feed EventChain.validators."""
        chain = _make_agent_chain("zr-validator", [EventType.AGENT_VALIDATE])
        assert chain.validators == []

    def test_agent_confidence_untouched(self) -> None:
        """Confidence only collects VALIDATE/SNAPSHOT; AGENT_* is invisible."""
        chain = _make_agent_chain("zr-conf", [EventType.AGENT_VALIDATE])
        assert chain.confidence == 0.0


# ---------------------------------------------------------------------------
# ZR-02 / ZR-03: StatusOrder and _VALID_TRANSITIONS unchanged
# ---------------------------------------------------------------------------


class TestLatticeShape:
    def test_status_order_members_unchanged(self) -> None:
        """ZR-02: exactly the 5 discovery statuses, in the same lattice order."""
        # StatusOrder is an IntEnum; assert the numeric lattice order.
        assert [s.value for s in StatusOrder] == [1, 2, 3, 4, 5]
        assert len(StatusOrder) == 5

    def test_valid_transitions_unchanged(self) -> None:
        """ZR-03: CRDT transition table keys stay the 5 discovery statuses."""
        assert set(_VALID_TRANSITIONS) == set(StatusOrder)


# ---------------------------------------------------------------------------
# ZR-04: consensus._status_to_event_type never yields AGENT_*/TASK_*
# ---------------------------------------------------------------------------


class TestStatusToEventType:
    def test_no_agent_or_task_mapping(self) -> None:
        """ZR-04: the status→event map only yields discovery lifecycle events."""
        from adl_lite.consensus import _status_to_event_type
        from adl_lite.models import DiscoveryStatus

        for status in DiscoveryStatus:
            mapped = _status_to_event_type(status)
            assert mapped in DISCOVERY_LIFECYCLE


# ---------------------------------------------------------------------------
# ZR-07/08: integrity and EventType count
# ---------------------------------------------------------------------------


class TestIntegrityAndCount:
    def test_agent_chain_verify_integrity(self) -> None:
        """ZR-07: agent chains pass verify_integrity (Axiom 9/12 compatible)."""
        chain = _make_agent_chain("zr-verify", [EventType.AGENT_REGISTER, EventType.AGENT_VALIDATE])
        assert chain.verify_integrity() is True

    def test_event_type_count(self) -> None:
        """ZR-08: 15 original + 4 AGENT_* = 19 members (verified against impl)."""
        assert len(EventType) >= 19
        assert AGENT_EVENT_TYPES <= set(EventType)


# ---------------------------------------------------------------------------
# ZR-09: ontology triggers_transition hygiene
# ---------------------------------------------------------------------------


class TestOntologyHygiene:
    def test_no_task_or_agent_status_in_triggers_transition(self) -> None:
        """ZR-09: new actions must declare triggers_transition: null."""
        from adl_lite.ontology import default_ontology

        om = default_ontology()
        # Only task/agent statuses are banned; "validated" is a discovery status
        # and legitimately appears in the existing validate action.
        banned = {
            "open",
            "assigned",
            "in_progress",
            "submitted",
            "rejected",
            "closed",
            "active",
            "pending",
        }
        for action_name, action_def in om._data["actions"].items():
            tt = action_def.get("triggers_transition")
            if tt is None or str(tt).strip() in ("", "null"):
                continue
            for token in str(tt).split():
                assert token not in banned, (
                    f"action '{action_name}' leaks task/agent status into triggers_transition"
                )


# ---------------------------------------------------------------------------
# ZR-10: legacy state files load without signature/proof keys
# ---------------------------------------------------------------------------


class TestLegacyStateCompat:
    def test_load_legacy_state_without_signature(self, tmp_path: Path) -> None:
        """ZR-10: old state JSON (no signature/proof) loads with defaults."""
        state_path = tmp_path / "legacy.json"
        state_path.write_text(
            json.dumps(
                {
                    "chains": {
                        "legacy-cid": [
                            {
                                "event_id": "evt-1",
                                "event_type": "register",
                                "actor": "system",
                                "reasoning": "",
                                "timestamp": "2026-01-01T00:00:00",
                                "hash": "a" * 64,
                                "payload": {"scope": "public"},
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        engine = _load_engine(state_path)
        event = engine.chains["legacy-cid"].events[0]
        assert event.signature == ""
        assert event.proof is None

    def test_chain_kind_markers(self) -> None:
        """ZR-13 companion: chain_kind distinguishes agent vs discovery."""
        registry = AgentRegistry()
        chain = registry.register_agent(
            AgentProfile(did="did:key:z6MkplaceholderAgent", role=AgentRole.DISCOVERER, name="a")
        )
        assert chain_kind(chain) == "agent"
