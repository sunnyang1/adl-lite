"""
Tests for adl_lite.ld_proof — Ed25519 signing over canonical event JSON.
"""

from __future__ import annotations

from adl_lite.ld_proof import generate_keypair, sign_event, verify_event_signature
from adl_lite.models import Event, EventType


class TestLDProof:
    """Validate sign + verify round-trip and tamper detection."""

    def test_sign_verify_roundtrip(self):
        event = Event(
            concept_id="ld-proof-test",
            event_type=EventType.REGISTER,
            actor="alice",
            timestamp="2024-01-15T09:00:00+00:00",
            payload={"confidence": 0.75},
        )
        sk = generate_keypair()
        signed = sign_event(event, sk)

        assert "proof" in signed
        assert signed["proof"]["type"] == "Ed25519Signature2020"
        assert verify_event_signature(signed, sk.public_key())

    def test_tampered_event_fails_verification(self):
        event = Event(
            concept_id="ld-proof-tamper",
            event_type=EventType.VALIDATE,
            actor="bob",
            timestamp="2024-01-15T10:00:00+00:00",
        )
        sk = generate_keypair()
        signed = sign_event(event, sk)

        # Tamper with payload
        signed["payload"]["confidence"] = 0.99
        assert not verify_event_signature(signed, sk.public_key())

    def test_tampered_timestamp_fails_verification(self):
        event = Event(
            concept_id="ld-proof-ts",
            event_type=EventType.REGISTER,
            actor="charlie",
            timestamp="2024-01-15T09:00:00+00:00",
        )
        sk = generate_keypair()
        signed = sign_event(event, sk)

        # Tamper with timestamp
        signed["timestamp"] = "2025-12-25T00:00:00+00:00"
        assert not verify_event_signature(signed, sk.public_key())

    def test_auto_reconstruct_public_key(self):
        event = Event(
            concept_id="ld-proof-auto",
            event_type=EventType.REGISTER,
            actor="dave",
        )
        sk = generate_keypair()
        signed = sign_event(event, sk)

        # Verify without passing public key explicitly
        assert verify_event_signature(signed)

    def test_missing_proof_returns_false(self):
        event = Event(
            concept_id="ld-proof-missing",
            event_type=EventType.REGISTER,
            actor="eve",
        )
        signed = {
            "event_id": event.event_id,
            "concept_id": event.concept_id,
            "event_type": event.event_type.value,
            "actor": event.actor,
            "reasoning": event.reasoning,
            "timestamp": event.timestamp,
            "payload": event.payload,
            "previous_event_id": event.previous_event_id,
            "hash": event.hash,
        }
        assert not verify_event_signature(signed)
