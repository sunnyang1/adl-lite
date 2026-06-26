"""
Linked Data Proofs for ADL Lite events.

Supports W3C Data Integrity style proofs:
  - Ed25519Signature2020
  - EcdsaSecp256k1Signature2019 (for did:ethr / secp256k1 keys)

A proof is stored on Event.proof and verified during EventChain.verify_integrity().
"""

from __future__ import annotations

import base64
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from .models import Event


def _did_resolver():
    """Lazy import DID resolver to avoid circular imports."""
    from . import did_resolver

    return did_resolver


def _canonical_event_json(event: Event) -> bytes:
    """
    Produce a canonical byte serialization of the event for signing.

    Excludes the hash field and proof field to avoid circular self-reference.
    """
    from .models import CANON_VERSION, _round_floats

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
        "canon_version": CANON_VERSION,
    }
    return json.dumps(content, sort_keys=True, default=str).encode("utf-8")


def generate_keypair() -> ed25519.Ed25519PrivateKey:
    """Generate a new Ed25519 keypair."""
    return ed25519.Ed25519PrivateKey.generate()


def create_event_proof(
    event: Event,
    private_key: ed25519.Ed25519PrivateKey,
    *,
    verification_method: str | None = None,
) -> dict[str, Any]:
    """
    Create an LD-Proof object for *event* without mutating the event.

    Args:
        event: The event to sign.
        private_key: Ed25519 private key.
        verification_method: DID URL or base64 public key. If omitted, uses base64 key.
    """
    canonical = _canonical_event_json(event)
    signature = private_key.sign(canonical)

    if verification_method is None:
        verification_method = base64.b64encode(private_key.public_key().public_bytes_raw()).decode(
            "ascii"
        )

    from datetime import datetime, timezone

    return {
        "type": "Ed25519Signature2020",
        "created": datetime.now(timezone.utc).isoformat(),
        "proofPurpose": "assertionMethod",
        "verificationMethod": verification_method,
        "proofValue": base64.b64encode(signature).decode("ascii"),
    }


def sign_event(
    event: Event,
    private_key: ed25519.Ed25519PrivateKey,
    *,
    verification_method: str | None = None,
) -> dict[str, Any]:
    """
    Sign an event's canonical JSON with Ed25519.

    Returns a dict containing the event fields plus a 'proof' object (legacy API).
    """
    proof = create_event_proof(event, private_key, verification_method=verification_method)

    from .models import CANON_VERSION

    event_dict = {
        "event_id": event.event_id,
        "concept_id": event.concept_id,
        "event_type": event.event_type.value,
        "actor": event.actor,
        "reasoning": event.reasoning,
        "timestamp": event.timestamp,
        "payload": event.payload,
        "previous_event_id": event.previous_event_id,
        "prev_hash": event._prev_hash,
        "hash": event.hash,
        "canon_version": CANON_VERSION,
    }
    event_dict["proof"] = proof
    return event_dict


def verify_event_signature(
    signed_event: dict[str, Any],
    public_key: ed25519.Ed25519PublicKey | None = None,
) -> bool:
    """
    Verify an event's Ed25519 signature from a signed-event dict.

    Legacy helper; prefer verify_event_proof() for Event objects.
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

    from .models import CANON_VERSION

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
        "canon_version": signed_event.get("canon_version", CANON_VERSION),
    }
    canonical = json.dumps(content, sort_keys=True, default=str).encode("utf-8")

    try:
        signature = base64.b64decode(proof["proofValue"])
        public_key.verify(signature, canonical)
        return True
    except (InvalidSignature, Exception):
        return False


def verify_event_proof(event: Event, *, resolver=None) -> bool:
    """
    Verify the LD-Proof on an Event.

    The verificationMethod may be:
      - a did:key / did:web / did:ethr DID URL,
      - a base64-encoded Ed25519 public key (legacy fallback).
    """
    proof = event.proof
    if not proof:
        return True  # No proof to verify is valid

    proof_type = proof.get("type", "")
    proof_value = proof.get("proofValue", "")
    verification_method = proof.get("verificationMethod", "")
    proof_purpose = proof.get("proofPurpose", "assertionMethod")

    if proof_purpose != "assertionMethod":
        return False

    canonical = _canonical_event_json(event)

    try:
        signature = base64.b64decode(proof_value)
    except Exception:
        return False

    if proof_type == "Ed25519Signature2020":
        return _verify_ed25519_signature(
            verification_method, canonical, signature, resolver=resolver
        )
    if proof_type == "EcdsaSecp256k1Signature2019":
        return _verify_secp256k1_signature(
            verification_method, canonical, signature, resolver=resolver
        )

    return False


def _verify_ed25519_signature(
    verification_method: str, message: bytes, signature: bytes, *, resolver=None
) -> bool:
    """Resolve an Ed25519 public key and verify a signature."""
    dr = _did_resolver()

    # DID URL?
    if verification_method.startswith("did:"):
        did = verification_method.split("#")[0]
        doc = dr.resolve_did(did, rpc_url=getattr(resolver, "rpc_url", None))
        vm = doc.key_for_purpose("assertionMethod")
        if vm is None or vm.type not in (
            "Ed25519VerificationKey2020",
            "Ed25519VerificationKey2018",
        ):
            return False
        pk = ed25519.Ed25519PublicKey.from_public_bytes(vm.public_key_bytes)
        pk.verify(signature, message)
        return True

    # Raw base64 public key fallback
    try:
        pk_bytes = base64.b64decode(verification_method)
        pk = ed25519.Ed25519PublicKey.from_public_bytes(pk_bytes)
        pk.verify(signature, message)
        return True
    except Exception:
        return False


def _verify_secp256k1_signature(
    verification_method: str, message: bytes, signature: bytes, *, resolver=None
) -> bool:
    """Resolve a secp256k1 public key or did:ethr address and verify a signature."""
    dr = _did_resolver()

    if verification_method.startswith("did:ethr:"):
        did = verification_method.split("#")[0]
        return bool(
            dr.verify_did_signature(
                did, message, signature, rpc_url=getattr(resolver, "rpc_url", None)
            )
        )

    # Raw public key or did:web with secp256k1 VM
    if verification_method.startswith("did:"):
        did = verification_method.split("#")[0]
        doc = dr.resolve_did(did, rpc_url=getattr(resolver, "rpc_url", None))
        vm = doc.key_for_purpose("assertionMethod")
        if vm is None or vm.type not in (
            "EcdsaSecp256k1VerificationKey2019",
            "EcdsaSecp256k1RecoveryMethod2020",
        ):
            return False
        return bool(dr._verify_secp256k1_signature(vm.public_key_bytes, message, signature))

    try:
        pk_bytes = base64.b64decode(verification_method)
        return bool(dr._verify_secp256k1_signature(pk_bytes, message, signature))
    except Exception:
        return False
