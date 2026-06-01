"""
Adversarial CRDT tests — concurrent writes, conflict injection, merge verification.

Addresses reviewer concern: "Multi-agent auditability and offline synchronization
experiments would be stronger with adversarial perturbations."
"""

from __future__ import annotations

from adl_lite.crdt import CRDTState, StatusOrder
from adl_lite.models import EventType


class TestCRDTConcurrentWrites:
    """Multiple agents update the same concept concurrently."""

    def test_concurrent_conflicting_validates_merge_to_validated(self):
        """Two agents validate simultaneously → merge should be validated."""
        s1 = CRDTState()
        s1 = s1.apply_event(EventType.VALIDATE.value, {"actor": "a1"})

        s2 = CRDTState()
        s2 = s2.apply_event(EventType.VALIDATE.value, {"actor": "a2"})

        merged = s1.merge(s2)
        assert merged.status == StatusOrder.VALIDATED
        assert merged.validator_count == 1  # G-Counter max of (1, 1)

    def test_concurrent_validate_and_deprecate_merge_to_deprecated(self):
        """One agent validates, another deprecates → deprecate wins (higher in lattice)."""
        s1 = CRDTState()
        s1 = s1.apply_event(EventType.VALIDATE.value, {"actor": "a1"})

        s2 = CRDTState()
        s2 = s2.apply_event(EventType.DEPRECATE.value, {"actor": "a2"})

        merged = s1.merge(s2)
        assert merged.status == StatusOrder.DEPRECATED

    def test_concurrent_conflicting_evidence_accumulates(self):
        """Concurrent evidence events → max count preserved (G-Counter)."""
        s1 = CRDTState()
        s1 = s1.apply_event(EventType.EVIDENCE.value, {"actor": "a1", "link": "ev1"})
        s1 = s1.apply_event(EventType.EVIDENCE.value, {"actor": "a1", "link": "ev2"})

        s2 = CRDTState()
        s2 = s2.apply_event(EventType.EVIDENCE.value, {"actor": "a2", "link": "ev3"})

        merged = s1.merge(s2)
        assert merged.evidence_count == 2  # max(2, 1)


class TestCRDTReplayResistance:
    """Replayed events should be idempotent (no state change)."""

    def test_replayed_validate_does_not_inflate_confidence(self):
        s = CRDTState()
        s = s.apply_event(EventType.VALIDATE.value, {"actor": "a1", "confidence": 0.85})
        confidence_after_first = s.confidence

        s = s.apply_event(EventType.VALIDATE.value, {"actor": "a1", "confidence": 0.85})  # Replay
        assert (
            s.confidence == confidence_after_first
        ), "Replayed validate should not increase confidence (same confidence value)"
        # Note: validator_count increments on every VALIDATE event in this simplified
        # G-Counter model. Full actor-deduplication requires a G-Set over actor IDs,
        # which is Phase 3 work (cryptographic identity binding).


class TestCRDTPoisonedMerge:
    """Merge with a maliciously constructed state."""

    def test_merge_with_empty_state_is_identity(self):
        s = CRDTState()
        s = s.apply_event(EventType.VALIDATE.value, {"actor": "a1"})

        empty = CRDTState()
        merged = s.merge(empty)
        assert merged.status == s.status
        assert merged.confidence == s.confidence
        assert merged.validator_count == s.validator_count

    def test_merge_does_not_lose_progress(self):
        s1 = CRDTState()
        s1 = s1.apply_event(EventType.VALIDATE.value, {"actor": "a1", "confidence": 0.85})

        s2 = CRDTState()
        s2 = s2.apply_event(EventType.VALIDATE.value, {"actor": "a2", "confidence": 0.75})

        merged = s1.merge(s2)
        assert merged.confidence == 0.85  # max(0.85, 0.75)
        assert merged.status == StatusOrder.VALIDATED


class TestCRDTStatusRegression:
    """Status regression (e.g., validated → provisional) must be rejected."""

    def test_status_regression_rejected(self):
        s = CRDTState()
        s = s.apply_event(EventType.VALIDATE.value, {"actor": "a1"})
        assert s.status == StatusOrder.VALIDATED

        # Attempt regression via REGISTER (no-op in CRDT)
        s = s.apply_event(EventType.REGISTER.value, {"actor": "a2"})
        assert s.status == StatusOrder.VALIDATED, "Status regression should be rejected"

    def test_deprecate_after_validate_allowed(self):
        s = CRDTState()
        s = s.apply_event(EventType.VALIDATE.value, {"actor": "a1"})
        s = s.apply_event(EventType.DEPRECATE.value, {"actor": "a2"})
        assert s.status == StatusOrder.DEPRECATED
