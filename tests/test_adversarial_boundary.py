"""
Boundary tests (B1–B4) for known limitations in the ADL Lite trust model.

These tests document attack scenarios that verify_integrity() cannot detect
because the attacker recomputes valid hashes. They are negative tests: they
confirm that the structural integrity check alone is insufficient against
these threat classes, which is a documented Phase 1 limitation.

B1: Collusion attack — already covered by E14/E20b (test_E20b.py)
B2: Genesis replacement — replace entire chain with re-computed hashes
B3: Impersonation — forge events with another actor's actor string
B4: Timestamp backdating — modify timestamp and re-compute hash
"""

from __future__ import annotations

from adl_lite.models import Event, EventChain, EventType


class TestBoundaryB2GenesisReplacement:
    """B2: Attacker replaces entire chain with re-computed hashes.

    verify_integrity() passes because the new chain is structurally valid,
    but the semantic content has been altered. Detection requires external
    anchoring (Git reflog, DIDs, transparency logs).
    """

    def test_genesis_replacement_with_valid_hashes_passes(self):
        """Replace entire chain — verify_integrity() passes (known limitation)."""
        # Original chain
        chain = EventChain(concept_id="b2-original")
        chain.append(
            Event(
                concept_id="b2-original",
                event_type=EventType.REGISTER,
                actor="alice",
                payload={"description": "original"},
            )
        )
        chain.append(
            Event(
                concept_id="b2-original",
                event_type=EventType.VALIDATE,
                actor="bob",
                payload={"confidence": 0.85},
            )
        )
        assert chain.verify_integrity()

        # Attacker replaces the entire chain with a different content
        # but valid hash structure
        malicious_chain = EventChain(concept_id="b2-original")
        malicious_chain.append(
            Event(
                concept_id="b2-original",
                event_type=EventType.REGISTER,
                actor="alice",
                payload={"description": "MALICIOUS"},
            )
        )
        malicious_chain.append(
            Event(
                concept_id="b2-original",
                event_type=EventType.VALIDATE,
                actor="bob",
                payload={"confidence": 0.99},
            )
        )
        # verify_integrity() passes because hashes are valid
        assert malicious_chain.verify_integrity(), (
            "B2: Genesis replacement passes verify_integrity() — "
            "this is a known Phase 1 limitation requiring external anchoring"
        )

        # But the content is different
        assert (
            chain._events[0].payload != malicious_chain._events[0].payload
        )

    def test_genesis_replacement_different_status(self):
        """Attacker replaces validated chain with provisional-only chain."""
        # Original: validated chain
        original = EventChain(concept_id="b2-status")
        original.append(
            Event(
                concept_id="b2-status",
                event_type=EventType.REGISTER,
                actor="alice",
            )
        )
        original.append(
            Event(
                concept_id="b2-status",
                event_type=EventType.VALIDATE,
                actor="bob",
                payload={"confidence": 0.85},
            )
        )
        assert original.status.name == "VALIDATED"

        # Attacker replaces with a provisional-only chain
        malicious = EventChain(concept_id="b2-status")
        malicious.append(
            Event(
                concept_id="b2-status",
                event_type=EventType.REGISTER,
                actor="alice",
            )
        )
        # No VALIDATE event
        assert malicious.status.name == "PROVISIONAL"
        assert malicious.verify_integrity(), (
            "B2: Replaced chain passes verify_integrity() despite different status"
        )


class TestBoundaryB3Impersonation:
    """B3: Attacker forges events with another actor's actor string.

    verify_integrity() does not detect this because actor is a plain string
    with no cryptographic binding in Phase 1. Detection requires Ed25519
    signatures + DIDs (Phase 3).
    """

    def test_impersonation_without_signature_passes(self):
        """Forge VALIDATE as another actor — verify_integrity() passes."""
        chain = EventChain(concept_id="b3-impersonate")
        chain.append(
            Event(
                concept_id="b3-impersonate",
                event_type=EventType.REGISTER,
                actor="alice",
            )
        )
        # Attacker forges a VALIDATE event as bob
        chain.append(
            Event(
                concept_id="b3-impersonate",
                event_type=EventType.VALIDATE,
                actor="bob",  # Forged — not actually bob
                payload={"confidence": 0.99},
            )
        )
        # verify_integrity() passes because actor is just a string
        assert chain.verify_integrity(), (
            "B3: Impersonation passes verify_integrity() without signature — "
            "known Phase 1 limitation"
        )

    def test_impersonation_increases_confidence(self):
        """Attacker impersonates multiple validators to inflate confidence."""
        chain = EventChain(concept_id="b3-collude")
        chain.append(
            Event(
                concept_id="b3-collude",
                event_type=EventType.REGISTER,
                actor="alice",
            )
        )
        # Attacker forges multiple validators
        for actor in ["bob", "charlie", "dave", "eve", "frank"]:
            chain.append(
                Event(
                    concept_id="b3-collude",
                    event_type=EventType.VALIDATE,
                    actor=actor,  # All forged by the same attacker
                    payload={"confidence": 0.99},
                )
            )
        assert chain.verify_integrity(), (
            "B3: Multiple impersonations pass verify_integrity() — "
            "detection requires signature verification (Phase 3)"
        )


class TestBoundaryB4TimestampBackdating:
    """B4: Attacker modifies timestamp and re-computes hash.

    verify_integrity() passes because timestamp is included in the hash
    input, so the attacker can recompute a valid hash. Detection requires
    signed timestamps (NTP + LD-Proofs) or external anchoring.
    """

    def test_backdating_with_hash_recomputation_passes(self):
        """Modify timestamp and recompute hash — verify_integrity() passes."""
        chain = EventChain(concept_id="b4-backdate")
        e1 = Event(
            concept_id="b4-backdate",
            event_type=EventType.REGISTER,
            actor="alice",
            timestamp="2024-01-15T09:00:00+00:00",
        )
        e2 = Event(
            concept_id="b4-backdate",
            event_type=EventType.VALIDATE,
            actor="bob",
            timestamp="2024-01-15T14:30:00+00:00",
        )
        chain.append(e1)
        chain.append(e2)
        assert chain.verify_integrity()

        # Attacker backdates e1 to an earlier time and recomputes hash
        chain._events[0].timestamp = "2023-01-01T00:00:00+00:00"
        chain._events[0].hash = chain._events[0]._compute_hash()
        # Recompute e2's prev_hash to link to the new e1 hash
        object.__setattr__(chain._events[1], "_prev_hash", chain._events[0].hash)
        chain._events[1].hash = chain._events[1]._compute_hash()

        # verify_integrity() passes because the attacker recomputed all hashes
        assert chain.verify_integrity(), (
            "B4: Timestamp backdating with hash recomputation passes "
            "verify_integrity() — known Phase 1 limitation"
        )

    def test_backdating_changes_event_order(self):
        """Backdating can make a later event appear earlier."""
        chain = EventChain(concept_id="b4-order")
        e1 = Event(
            concept_id="b4-order",
            event_type=EventType.REGISTER,
            actor="alice",
            timestamp="2024-06-15T10:00:00+00:00",
        )
        e2 = Event(
            concept_id="b4-order",
            event_type=EventType.VALIDATE,
            actor="bob",
            timestamp="2024-06-15T11:00:00+00:00",
        )
        chain.append(e1)
        chain.append(e2)
        assert chain.verify_integrity()

        # Attacker backdates e2 to appear before e1
        chain._events[1].timestamp = "2024-06-15T09:00:00+00:00"
        chain._events[1].hash = chain._events[1]._compute_hash()
        object.__setattr__(chain._events[1], "_prev_hash", chain._events[0].hash)
        # e1 hash unchanged

        # This is a structural anomaly: e2's timestamp < e1's timestamp
        # but e2's previous_event_id links to e1. The verify_integrity()
        # does NOT check timestamp monotonicity (Axiom 7 checks timestamp
        # monotonicity, but the attacker recomputed hashes correctly).
        # Actually, let me check if Axiom 7 catches this.
        # Axiom 7: timestamp monotonicity (non-decreasing)
        # If e2's timestamp is backdated to before e1, this WOULD fail Axiom 7.
        # But the test above recomputes e2's hash, not e1's.
        # So e2's timestamp is 09:00, e1's is 10:00 — e2 < e1, which violates
        # monotonicity because e2 comes AFTER e1 in the chain.
        # So this should FAIL verify_integrity(full=True) if Axiom 7 is checked.
        # Let me verify this.
        result = chain.verify_integrity(full=True)
        assert not result, (
            "B4: Timestamp backdating that breaks monotonicity is detected "
            "by Axiom 7 (timestamp monotonicity)"
        )
