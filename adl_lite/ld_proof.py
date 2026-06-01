"""
Linked Data Proofs sketch for ADL Lite events.

This module provides a minimal Ed25519 signing wrapper over canonical
event JSON, demonstrating the Phase 3 path to cryptographically bound
actor identities.

Dependencies:
    pip install cryptography

Example usage:
    from adl_lite.ld_proof import sign_event, verify_event_signature
    from adl_lite.models import Event, EventType

    event = Event(concept_id="demo", event_type=EventType.REGISTER, actor="alice")
    private_key = generate_keypair()
    signed = sign_event(event, private_key)
    assert verify_event_signature(signed, private_key.public_key())
"""

from __future__ import annotations

import base64
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from .models import Event


def _canonical_event_json(event: Event) -> bytes:
    """
    Produce a canonical byte serialization of the event for signing.

    Rules (same as _compute_hash but without the hash field):
      - Exclude the hash field itself
      - Sort keys recursively
      - Round floats to 6 decimal places
      - Encode as UTF-8 JSON
    """
    from .models import _round_floats

    content = {
        "event_id": event.event_id,
        "concept_id": event.concept_id,
        "event_type": event.event_type.value,
        "actor": event.actor,
        "reasoning": event.reasoning,
        "timestamp": event.timestamp,
        "payload": _round_floats(event.payload),
        "previous_event_id": event.previous_event_id,
        "prev_hash": event._prev_hash,
    }
    return json.dumps(content, sort_keys=True, default=str).encode("utf-8")


def generate_keypair() -> ed25519.Ed25519PrivateKey:
    """Generate a new Ed25519 keypair."""
    return ed25519.Ed25519PrivateKey.generate()


def sign_event(event: Event, private_key: ed25519.Ed25519PrivateKey) -> dict[str, str]:
    """
    Sign an event's canonical JSON with Ed25519.

    Returns a dict containing the event fields plus a 'proof' object:
        {
            ...event fields...,
            "proof": {
                "type": "Ed25519Signature2020",
                "created": <ISO timestamp>,
                "proofPurpose": "assertionMethod",
                "verificationMethod": <base64 public key>,
                "proofValue": <base64 signature>
            }
        }
    """
    canonical = _canonical_event_json(event)
    signature = private_key.sign(canonical)

    public_key_b64 = base64.b64encode(private_key.public_key().public_bytes_raw()).decode("ascii")

    from datetime import datetime, timezone

    proof = {
        "type": "Ed25519Signature2020",
        "created": datetime.now(timezone.utc).isoformat(),
        "proofPurpose": "assertionMethod",
        "verificationMethod": public_key_b64,
        "proofValue": base64.b64encode(signature).decode("ascii"),
    }

    # Build a plain dict from the event (excluding internal hash machinery)
    event_dict = {
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
    event_dict["proof"] = proof
    return event_dict


def verify_event_signature(
    signed_event: dict[str, str],
    public_key: ed25519.Ed25519PublicKey | None = None,
) -> bool:
    """
    Verify an event's Ed25519 signature.

    If public_key is None, it is reconstructed from the
    verificationMethod field in the proof.
    """
    proof = signed_event.get("proof")
    if not proof:
        return False

    if public_key is None:
        try:
            pk_bytes = base64.b64decode(proof["verificationMethod"])
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pk_bytes)
        except Exception:
            return False

    # Reconstruct canonical bytes (exclude proof and hash)
    content = {
        "event_id": signed_event["event_id"],
        "concept_id": signed_event["concept_id"],
        "event_type": signed_event["event_type"],
        "actor": signed_event["actor"],
        "reasoning": signed_event["reasoning"],
        "timestamp": signed_event["timestamp"],
        "payload": signed_event["payload"],
        "previous_event_id": signed_event["previous_event_id"],
        "prev_hash": signed_event.get("prev_hash", ""),
    }
    canonical = json.dumps(content, sort_keys=True, default=str).encode("utf-8")

    try:
        signature = base64.b64decode(proof["proofValue"])
        public_key.verify(signature, canonical)
        return True
    except (InvalidSignature, Exception):
        return False
