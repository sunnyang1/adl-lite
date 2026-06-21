"""
Tests for Theorem 1 (Determinism) from the ADL Lite paper.

Theorem 1: For any well-formed chain C, δ(C) is unique and depends only on
the last lifecycle event in C.

Proof Sketch: δ filters to C_life, checks emptiness, and applies the total
function f to the last element.
"""

from __future__ import annotations

from adl_lite.models import DiscoveryStatus, Event, EventChain, EventType


class TestTheorem1Determinism:
    """T1: δ(C) is unique and depends only on the last lifecycle event."""

    def test_empty_lifecycle_is_provisional(self):
        """No lifecycle events → status is provisional."""
        chain = EventChain(concept_id="t1-empty")
        chain.append(
            Event(
                concept_id="t1-empty",
                event_type=EventType.RELATE,
                actor="agent",
                payload={"predicate": "isomorphic-to", "target": "other"},
            )
        )
        assert chain.status == DiscoveryStatus.PROVISIONAL

    def test_register_as_last_lifecycle(self):
        """Last lifecycle event is REGISTER → provisional."""
        chain = EventChain(concept_id="t1-reg")
        chain.append(Event(concept_id="t1-reg", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t1-reg",
                event_type=EventType.EVIDENCE,
                actor="a",
                payload={"url": "https://example.com"},
            )
        )
        assert chain.status == DiscoveryStatus.PROVISIONAL

    def test_validate_as_last_lifecycle(self):
        """Last lifecycle event is VALIDATE → validated."""
        chain = EventChain(concept_id="t1-val")
        chain.append(Event(concept_id="t1-val", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t1-val",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.85},
            )
        )
        chain.append(
            Event(
                concept_id="t1-val",
                event_type=EventType.RELATE,
                actor="a",
                payload={"predicate": "related-to", "target": "other"},
            )
        )
        assert chain.status == DiscoveryStatus.VALIDATED

    def test_deprecate_after_validate(self):
        """Last lifecycle event is DEPRECATE → deprecated."""
        chain = EventChain(concept_id="t1-dep")
        chain.append(Event(concept_id="t1-dep", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t1-dep",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.85},
            )
        )
        chain.append(Event(concept_id="t1-dep", event_type=EventType.DEPRECATE, actor="a"))
        chain.append(
            Event(
                concept_id="t1-dep",
                event_type=EventType.EVIDENCE,
                actor="c",
                payload={"note": "post-deprecation evidence"},
            )
        )
        assert chain.status == DiscoveryStatus.DEPRECATED

    def test_archive_as_last_lifecycle(self):
        """Last lifecycle event is ARCHIVE → archived."""
        chain = EventChain(concept_id="t1-arch")
        chain.append(Event(concept_id="t1-arch", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t1-arch",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.85},
            )
        )
        chain.append(Event(concept_id="t1-arch", event_type=EventType.ARCHIVE, actor="a"))
        assert chain.status == DiscoveryStatus.ARCHIVED

    def test_communication_events_do_not_change_status(self):
        """Communication events (RELATE, EVIDENCE, SEAL) do not affect status."""
        chain = EventChain(concept_id="t1-comm")
        chain.append(Event(concept_id="t1-comm", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t1-comm",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.75},
            )
        )
        # Append multiple communication events
        for i in range(5):
            chain.append(
                Event(
                    concept_id="t1-comm",
                    event_type=EventType.EVIDENCE,
                    actor="c",
                    payload={"note": f"evidence {i}"},
                )
            )
        chain.append(
            Event(
                concept_id="t1-comm",
                event_type=EventType.RELATE,
                actor="d",
                payload={"predicate": "isomorphic-to", "target": "other"},
            )
        )
        chain.append(
            Event(
                concept_id="t1-comm",
                event_type=EventType.SEAL,
                actor="e",
                payload={"hash": "abc123"},
            )
        )
        assert chain.status == DiscoveryStatus.VALIDATED

    def test_uniqueness_for_same_last_lifecycle(self):
        """Different prefixes with same last lifecycle → same δ(C)."""
        # Chain A: REGISTER → VALIDATE → EVIDENCE
        chain_a = EventChain(concept_id="t1-uniq-a")
        chain_a.append(Event(concept_id="t1-uniq-a", event_type=EventType.REGISTER, actor="a"))
        chain_a.append(
            Event(
                concept_id="t1-uniq-a",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.8},
            )
        )
        chain_a.append(
            Event(
                concept_id="t1-uniq-a",
                event_type=EventType.EVIDENCE,
                actor="c",
                payload={"note": "extra"},
            )
        )

        # Chain B: REGISTER → VALIDATE → RELATE → SEAL
        chain_b = EventChain(concept_id="t1-uniq-b")
        chain_b.append(Event(concept_id="t1-uniq-b", event_type=EventType.REGISTER, actor="a"))
        chain_b.append(
            Event(
                concept_id="t1-uniq-b",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.9},
            )
        )
        chain_b.append(
            Event(
                concept_id="t1-uniq-b",
                event_type=EventType.RELATE,
                actor="c",
                payload={"predicate": "related-to", "target": "x"},
            )
        )
        chain_b.append(
            Event(
                concept_id="t1-uniq-b",
                event_type=EventType.SEAL,
                actor="d",
                payload={"hash": "xyz"},
            )
        )

        # Both have VALIDATE as last lifecycle → both validated
        assert chain_a.status == chain_b.status == DiscoveryStatus.VALIDATED

    def test_deprecate_after_validate_then_re_register(self):
        """DEPRECATE then new REGISTER → stays deprecated (CRDT LUB semantics).

        Under CRDT semantics, once a concept reaches DEPRECATED, it never
        regresses to PROVISIONAL. A new REGISTER on the same chain is a
        no-op for status; re-activation requires a FORK to a new concept.
        """
        chain = EventChain(concept_id="t1-re-reg")
        chain.append(Event(concept_id="t1-re-reg", event_type=EventType.REGISTER, actor="a"))
        chain.append(
            Event(
                concept_id="t1-re-reg",
                event_type=EventType.VALIDATE,
                actor="b",
                payload={"confidence": 0.85},
            )
        )
        chain.append(Event(concept_id="t1-re-reg", event_type=EventType.DEPRECATE, actor="a"))
        # Re-activation via REGISTER on the same chain is a no-op (LUB stays DEPRECATED)
        chain.append(Event(concept_id="t1-re-reg", event_type=EventType.REGISTER, actor="a"))
        assert chain.status == DiscoveryStatus.DEPRECATED
