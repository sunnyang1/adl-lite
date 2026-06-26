"""
Tests for theorems from the ADL Lite paper.

- T4: Boundedness — confidence ∈ [0,1]
- T5: Monotonicity — status only moves forward in lifecycle
- T7: Well-formedness — 12 axioms hold
- T8: O(1) complexity — confidence and status computed in O(1)
"""

from __future__ import annotations

import time

import pytest

from adl_lite.models import (
    CANON_VERSION,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
)

# ============================================================================
# T4: Boundedness
# ============================================================================


class TestTheorem4Boundedness:
    """Theorem 4: confidence ∈ [0,1] for all VALIDATE events."""

    def test_confidence_clamped_to_1(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.VALIDATE,
                actor="agent",
                payload={"confidence": 1.5},
            )
        )
        assert chain.confidence == 1.0

    def test_confidence_clamped_to_0(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.VALIDATE,
                actor="agent",
                payload={"confidence": -0.5},
            )
        )
        assert chain.confidence == 0.0

    def test_aggregated_confidence_bounded(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.VALIDATE,
                actor="agent1",
                payload={"confidence": 0.9},
            )
        )
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.VALIDATE,
                actor="agent2",
                payload={"confidence": 0.9},
            )
        )
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.VALIDATE,
                actor="agent3",
                payload={"confidence": 0.9},
            )
        )
        agg = chain.aggregated_confidence()
        assert 0.0 <= agg <= 1.0

    def test_no_validate_events_confidence_zero(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.REGISTER,
                actor="agent",
            )
        )
        assert chain.confidence == 0.0


# ============================================================================
# T5: Monotonicity
# ============================================================================


class TestTheorem5Monotonicity:
    """Theorem 5: status only moves forward in lifecycle graph."""

    def test_register_then_validate(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.REGISTER, actor="a"))
        assert chain.status == DiscoveryStatus.PROVISIONAL
        chain.append(Event(concept_id="test", event_type=EventType.VALIDATE, actor="a"))
        assert chain.status == DiscoveryStatus.VALIDATED

    def test_validate_then_deprecate(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.VALIDATE, actor="a"))
        chain.append(Event(concept_id="test", event_type=EventType.DEPRECATE, actor="a"))
        assert chain.status == DiscoveryStatus.DEPRECATED

    def test_validate_then_archive(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.VALIDATE, actor="a"))
        chain.append(Event(concept_id="test", event_type=EventType.ARCHIVE, actor="a"))
        assert chain.status == DiscoveryStatus.ARCHIVED

    def test_status_never_regresses(self) -> None:
        """Once archived, cannot go back to validated (CRDT LUB semantics)."""
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.VALIDATE, actor="a"))
        chain.append(Event(concept_id="test", event_type=EventType.ARCHIVE, actor="a"))
        assert chain.status == DiscoveryStatus.ARCHIVED
        # Append a VALIDATE after ARCHIVE — CRDT LUB keeps ARCHIVED
        chain.append(Event(concept_id="test", event_type=EventType.VALIDATE, actor="a"))
        # The LUB of (ARCHIVED, VALIDATED) = ARCHIVED (status never regresses)
        assert chain.status == DiscoveryStatus.ARCHIVED


# ============================================================================
# T7: Well-formedness (12 axioms)
# ============================================================================


class TestTheorem7WellFormedness:
    """Theorem 7: all 12 well-formedness axioms hold."""

    def test_axiom_1_genesis_anchoring(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.REGISTER, actor="a"))
        assert chain.verify_integrity()

    def test_axiom_2_shared_concept(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.REGISTER, actor="a"))
        with pytest.raises(ValueError):
            chain.append(Event(concept_id="other", event_type=EventType.VALIDATE, actor="a"))

    def test_axiom_3_cryptographic_linkage(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.REGISTER, actor="a"))
        chain.append(Event(concept_id="test", event_type=EventType.VALIDATE, actor="a"))
        assert chain.verify_integrity()

    def test_axiom_4_hash_correctness(self) -> None:
        chain = EventChain(concept_id="test")
        e = Event(concept_id="test", event_type=EventType.REGISTER, actor="a")
        chain.append(e)
        assert e.hash == e._compute_hash()

    def test_axiom_5_distinct_event_ids(self) -> None:
        chain = EventChain(concept_id="test")
        e1 = Event(concept_id="test", event_type=EventType.REGISTER, actor="a")
        e2 = Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a",
            event_id=e1.event_id,  # Duplicate ID
        )
        chain.append(e1)
        chain.append(e2)
        assert not chain.verify_integrity()
        assert chain._check_wf5_distinct_event_ids() == [e1.event_id]

    def test_axiom_6_non_empty_actor(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.REGISTER, actor=""))
        assert not chain.verify_integrity()
        assert chain._check_wf6_non_empty_actor()

    def test_axiom_7_timestamp_monotonicity(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.REGISTER,
                actor="a",
                timestamp="2024-01-01T00:00:00+00:00",
            )
        )
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.VALIDATE,
                actor="a",
                timestamp="2024-01-01T00:00:00+00:00",  # Same timestamp is OK
            )
        )
        assert chain.verify_integrity()

    def test_axiom_7_timestamp_not_monotonic_fails(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.REGISTER,
                actor="a",
                timestamp="2024-01-02T00:00:00+00:00",
            )
        )
        # Bypass append() so that the backdated timestamp is preserved, testing
        # that verify_integrity detects the monotonicity violation.
        backdated = Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a",
            timestamp="2024-01-01T00:00:00+00:00",  # Earlier timestamp
        )
        chain._events.append(backdated)
        assert not chain.verify_integrity()
        assert chain._check_wf7_timestamp_monotonicity()

    def test_axiom_8_payload_schema(self) -> None:
        chain = EventChain(concept_id="test")
        e = Event(concept_id="test", event_type=EventType.REGISTER, actor="a")
        e.payload = "not a dict"  # type: ignore[assignment]
        chain.append(e)
        assert not chain.verify_integrity()
        assert chain._check_wf8_payload_schema()

    def test_axiom_9_action_preconditions(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.ANNOUNCE,
                actor="a",
                payload={"no_action_field": "test"},
            )
        )
        assert not chain.verify_integrity()
        assert chain._check_wf9_action_preconditions()

    def test_axiom_10_hash_algorithm(self) -> None:
        chain = EventChain(concept_id="test")
        e = Event(concept_id="test", event_type=EventType.REGISTER, actor="a")
        chain.append(e)
        e.hash = "too_short"
        assert not chain.verify_integrity()
        assert chain._check_wf10_hash_algorithm()

    def test_axiom_11_canonical_fields(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.REGISTER, actor="a"))
        e = Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a",
            previous_event_id=None,  # Missing link
        )
        # Bypass append() to avoid it setting previous_event_id automatically
        chain._events.append(e)
        assert not chain.verify_integrity()
        assert chain._check_wf11_canonical_fields()

    def test_axiom_12_event_type_valid(self) -> None:
        chain = EventChain(concept_id="test")
        e = Event(concept_id="test", event_type=EventType.REGISTER, actor="a")
        # Manually corrupt event_type
        e.event_type = "invalid"  # type: ignore[assignment]
        chain.append(e)
        assert not chain.verify_integrity()
        assert chain._check_wf12_event_type_valid()

    def test_well_formedness_report(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.REGISTER, actor="a"))
        report = chain.well_formedness_report()
        for axiom, violations in report.items():
            assert violations == [], f"Axiom {axiom} failed unexpectedly"

    def test_integrity_violations(self) -> None:
        chain = EventChain(concept_id="test")
        chain.append(Event(concept_id="test", event_type=EventType.REGISTER, actor=""))
        violations = chain.integrity_violations()
        assert any("axiom_6" in v for v in violations)


# ============================================================================
# T8: O(1) complexity
# ============================================================================


class TestTheorem8O1Complexity:
    """Theorem 8: confidence and status computed in O(1) time."""

    def test_status_o1_vs_chain_length(self) -> None:
        """Status access time should not grow with chain length."""
        chain = EventChain(concept_id="test")
        for _ in range(100):
            chain.append(
                Event(
                    concept_id="test",
                    event_type=EventType.EVIDENCE,
                    actor="a",
                )
            )
        chain.append(Event(concept_id="test", event_type=EventType.VALIDATE, actor="a"))

        # Time status access
        start = time.perf_counter()
        for _ in range(1000):
            _ = chain.status
        elapsed = time.perf_counter() - start

        # Should be very fast (< 0.1s for 1000 accesses)
        assert elapsed < 0.1

    def test_confidence_o1_vs_chain_length(self) -> None:
        """Confidence access time should not grow with chain length."""
        chain = EventChain(concept_id="test")
        for _ in range(100):
            chain.append(
                Event(
                    concept_id="test",
                    event_type=EventType.EVIDENCE,
                    actor="a",
                )
            )
        chain.append(
            Event(
                concept_id="test",
                event_type=EventType.VALIDATE,
                actor="a",
                payload={"confidence": 0.85},
            )
        )

        start = time.perf_counter()
        for _ in range(1000):
            _ = chain.confidence
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1

    def test_aggregated_confidence_not_o1(self) -> None:
        """aggregated_confidence() is O(N) by design — this is OK."""
        chain = EventChain(concept_id="test")
        for i in range(50):
            chain.append(
                Event(
                    concept_id="test",
                    event_type=EventType.VALIDATE,
                    actor=f"agent_{i}",
                    payload={"confidence": 0.5},
                )
            )
        agg = chain.aggregated_confidence()
        assert 0.0 <= agg <= 1.0


# ============================================================================
# Canon version in hash
# ============================================================================


class TestCanonVersion:
    """Test that canon_version is included in event hash."""

    def test_canon_version_constant(self) -> None:
        assert CANON_VERSION == "1.0"

    def test_hash_includes_canon_version(self) -> None:
        e = Event(concept_id="test", event_type=EventType.REGISTER, actor="a")
        # Hash should be 64 hex chars
        assert len(e.hash) == 64
        # Verify hash computation includes canon_version by comparing
        # with a manual computation
        import hashlib
        import json

        from adl_lite.models import CANON_VERSION, _round_floats

        hash_content = {
            "event_id": e.event_id,
            "concept_id": e.concept_id,
            "event_type": e.event_type.value,
            "actor": e.actor,
            "timestamp": e.timestamp,
            "payload": _round_floats(e.payload),
            "previous_event_id": e.previous_event_id,
            "prev_hash": e._prev_hash,
            "canon_version": CANON_VERSION,
        }
        expected = hashlib.sha256(
            json.dumps(hash_content, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        assert e.hash == expected


# ============================================================================
# CRDT merge (Theorem 9)
# ============================================================================


class TestTheorem9CRDTMerge:
    """Theorem 9: LWW-Set merge of EventChains is commutative, associative, idempotent."""

    def test_merge_commutative(self) -> None:
        from adl_lite.crdt import merge_event_chains

        a = EventChain(concept_id="test")
        a.append(Event(concept_id="test", event_type=EventType.REGISTER, actor="a"))

        b = EventChain(concept_id="test")
        b.append(Event(concept_id="test", event_type=EventType.VALIDATE, actor="b"))

        m1 = merge_event_chains(a, b)
        m2 = merge_event_chains(b, a)
        assert m1.length == m2.length
        # Events should have same IDs
        assert [e.event_id for e in m1.events] == [e.event_id for e in m2.events]

    def test_merge_idempotent(self) -> None:
        from adl_lite.crdt import merge_event_chains

        a = EventChain(concept_id="test")
        a.append(Event(concept_id="test", event_type=EventType.REGISTER, actor="a"))

        m = merge_event_chains(a, a)
        assert m.length == a.length
        assert [e.event_id for e in m.events] == [e.event_id for e in a.events]

    def test_merge_different_concept_ids_raises(self) -> None:
        from adl_lite.crdt import merge_event_chains

        a = EventChain(concept_id="a")
        b = EventChain(concept_id="b")
        with pytest.raises(ValueError):
            merge_event_chains(a, b)

    def test_merge_preserves_integrity(self) -> None:
        from adl_lite.crdt import merge_event_chains

        a = EventChain(concept_id="test")
        a.append(Event(concept_id="test", event_type=EventType.REGISTER, actor="a"))

        b = EventChain(concept_id="test")
        b.append(Event(concept_id="test", event_type=EventType.VALIDATE, actor="b"))

        m = merge_event_chains(a, b)
        assert m.verify_integrity()

    def test_merge_union_events(self) -> None:
        from adl_lite.crdt import merge_event_chains

        # Use the same genesis event in both chains so deduplication works
        genesis = Event(concept_id="test", event_type=EventType.REGISTER, actor="a")

        a = EventChain(concept_id="test")
        a.append(genesis)
        a.append(Event(concept_id="test", event_type=EventType.VALIDATE, actor="a"))

        b = EventChain(concept_id="test")
        b.append(genesis)
        b.append(Event(concept_id="test", event_type=EventType.EVIDENCE, actor="b"))

        m = merge_event_chains(a, b)
        # Should have 3 events: REGISTER, VALIDATE, EVIDENCE
        assert m.length == 3
        types = [e.event_type for e in m.events]
        assert EventType.REGISTER in types
        assert EventType.VALIDATE in types
        assert EventType.EVIDENCE in types
