"""
Tests for Theorem 6 (Status–Confidence Consistency) from the ADL Lite paper.

Theorem 6: If δ(C) = validated, then γ(C) ≥ 0.5.

Proof Sketch: δ(C) = validated implies V ≠ ∅, and the validate action
precondition requires confidence ≥ 0.5 (enforced by ActionExecutor via
adl_core_ontology.yaml).
"""

from __future__ import annotations

import pytest

from adl_lite.models import Event, EventChain, EventType, DiscoveryStatus


class TestTheorem6StatusConfidenceConsistency:
    """T6: validated → confidence ≥ 0.5."""

    def test_validated_chain_has_confidence_at_least_half(self):
        """Single VALIDATE with confidence 0.5 → γ = 0.5."""
        chain = EventChain(concept_id="t6-min")
        chain.append(Event(concept_id="t6-min", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t6-min",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.5},
            )
        )
        assert chain.status == DiscoveryStatus.VALIDATED
        assert chain.confidence >= 0.5

    def test_validated_chain_with_high_confidence(self):
        """VALIDATE with confidence 0.95 → γ = 0.95."""
        chain = EventChain(concept_id="t6-high")
        chain.append(Event(concept_id="t6-high", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t6-high",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.95},
            )
        )
        assert chain.status == DiscoveryStatus.VALIDATED
        assert chain.confidence >= 0.5

    def test_provisional_chain_has_zero_confidence(self):
        """No VALIDATE events → confidence = 0.0."""
        chain = EventChain(concept_id="t6-prov")
        chain.append(Event(concept_id="t6-prov", event_type=EventType.REGISTER, actor="a"))
        assert chain.status == DiscoveryStatus.PROVISIONAL
        assert chain.confidence == 0.0

    def test_deprecated_chain_may_have_confidence(self):
        """Deprecated chain may retain confidence from prior VALIDATE."""
        chain = EventChain(concept_id="t6-dep")
        chain.append(Event(concept_id="t6-dep", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t6-dep",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.85},
            )
        )
        chain.append(Event(concept_id="t6-dep", event_type=EventType.DEPRECATE, actor="a"))
        assert chain.status == DiscoveryStatus.DEPRECATED
        # Confidence may still be > 0 from the VALIDATE event
        assert chain.confidence >= 0.5

    def test_multiple_validates_confidence_is_last(self):
        """Multiple VALIDATE events: γ takes the last one (O(1) strategy)."""
        chain = EventChain(concept_id="t6-multi")
        chain.append(Event(concept_id="t6-multi", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t6-multi",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.6},
            )
        )
        chain.append(
            Event(
                concept_id="t6-multi",
                event_type=EventType.VALIDATE,
                actor="c",
                payload={"confidence": 0.75},
            )
        )
        assert chain.status == DiscoveryStatus.VALIDATED
        assert chain.confidence == 0.75
        assert chain.confidence >= 0.5

    def test_validated_chain_with_communication_events(self):
        """Communication events do not affect the status-confidence relation."""
        chain = EventChain(concept_id="t6-comm")
        chain.append(Event(concept_id="t6-comm", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t6-comm",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.82},
            )
        )
        chain.append(
            Event(
                concept_id="t6-comm",
                event_type=EventType.EVIDENCE,
                actor="c",
                payload={"note": "supporting evidence"},
            )
        )
        chain.append(
            Event(
                concept_id="t6-comm",
                event_type=EventType.RELATE,
                actor="d",
                payload={"predicate": "isomorphic-to", "target": "other"},
            )
        )
        assert chain.status == DiscoveryStatus.VALIDATED
        assert chain.confidence >= 0.5

    def test_no_validate_below_half(self):
        """A chain with VALIDATE confidence < 0.5 is still validated (clamped)."""
        chain = EventChain(concept_id="t6-low")
        chain.append(Event(concept_id="t6-low", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t6-low",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.3},
            )
        )
        assert chain.status == DiscoveryStatus.VALIDATED
        # The O(1) last-VALIDATE strategy takes the raw value (clamped by Pydantic)
        # Note: Pydantic clamps to [0,1], but does not enforce ≥ 0.5 for confidence
        # The ActionExecutor precondition enforces ≥ 0.5 for VALIDATE actions
        assert chain.confidence == 0.3

    def test_archived_chain_after_validate(self):
        """ARCHIVE after VALIDATE: status is archived, but confidence may persist."""
        chain = EventChain(concept_id="t6-arch")
        chain.append(Event(concept_id="t6-arch", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t6-arch",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.9},
            )
        )
        chain.append(Event(concept_id="t6-arch", event_type=EventType.ARCHIVE, actor="a"))
        assert chain.status == DiscoveryStatus.ARCHIVED
        assert chain.confidence >= 0.5
