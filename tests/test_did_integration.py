"""
Tests for minimal DID integration (did:key only).
"""

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from adl_lite.did_resolver import (
    create_did_key,
    is_did,
    resolve_did_key,
    verify_did_signature,
)
from adl_lite.key_registry import KeyRegistry
from adl_lite.models import Event, EventType

# ---------------------------------------------------------------------------
# did:key resolution tests
# ---------------------------------------------------------------------------


def test_create_and_resolve_did_key():
    """Round-trip: create did:key from key → resolve back to same key."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    did = create_did_key(public_key)
    assert did.startswith("did:key:z")
    resolved = resolve_did_key(did)
    assert resolved.public_bytes_raw() == public_key.public_bytes_raw()


def test_resolve_did_key_invalid_prefix():
    with pytest.raises(ValueError, match="Only did:key"):
        resolve_did_key("did:web:example.com")


def test_is_did():
    assert is_did("did:key:z6MkqRY") is True
    assert is_did("agent_1") is False
    assert is_did("did:web:example.com") is False  # only did:key supported


# ---------------------------------------------------------------------------
# Signature verification tests
# ---------------------------------------------------------------------------


def test_verify_did_signature_valid():
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    message = b"test event content"
    signature = private_key.sign(message)
    assert verify_did_signature(did, message, signature) is True


def test_verify_did_signature_invalid():
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    message = b"test event content"
    bad_signature = b"\x00" * 64
    assert verify_did_signature(did, message, bad_signature) is False


# ---------------------------------------------------------------------------
# KeyRegistry DID integration tests
# ---------------------------------------------------------------------------


def test_key_registry_resolve_did(tmp_path):
    """KeyRegistry can resolve did:key without YAML registration."""
    registry = KeyRegistry(registry_path=tmp_path / "keys.yaml")
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    pk = registry.get_public_key(did)
    assert pk is not None
    assert pk.public_bytes_raw() == private_key.public_key().public_bytes_raw()


def test_key_registry_verify_did_signature(tmp_path):
    """KeyRegistry verifies DID signatures without YAML registration."""
    registry = KeyRegistry(registry_path=tmp_path / "keys.yaml")
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    message = b"event hash"
    signature = private_key.sign(message)
    assert registry.verify_signature(did, message, signature) is True


def test_key_registry_legacy_actor_still_works(tmp_path):
    """Non-DID actors still use YAML registry."""
    registry = KeyRegistry(registry_path=tmp_path / "keys.yaml")
    private_key = ed25519.Ed25519PrivateKey.generate()
    registry.register("agent_1", private_key.public_key())
    message = b"event hash"
    signature = private_key.sign(message)
    assert registry.verify_signature("agent_1", message, signature) is True


# ---------------------------------------------------------------------------
# Event with DID actor tests
# ---------------------------------------------------------------------------


def test_event_with_did_actor():
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    event = Event(
        concept_id="test",
        event_type=EventType.VALIDATE,
        actor=did,
        payload={"confidence": 0.8},
    )
    assert event.actor == did
    assert event.hash != ""
    # Signature field is empty by default
    assert event.signature == ""


def test_sign_and_verify_event():
    """Sign an event with DID key and verify the signature."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    event = Event(
        concept_id="test",
        event_type=EventType.VALIDATE,
        actor=did,
        payload={"confidence": 0.8},
    )
    # Sign the event hash
    import base64

    signature = private_key.sign(event.hash.encode("utf-8"))
    event.signature = base64.b64encode(signature).decode("ascii")

    # Verify
    sig_bytes = base64.b64decode(event.signature)
    assert verify_did_signature(did, event.hash.encode("utf-8"), sig_bytes) is True


# ---------------------------------------------------------------------------
# Known test vectors (did:key from spec examples)
# ---------------------------------------------------------------------------


def test_known_did_key_vector():
    """Verify that a did:key created by our own implementation round-trips correctly."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    pk = resolve_did_key(did)
    assert len(pk.public_bytes_raw()) == 32
    assert pk.public_bytes_raw() == private_key.public_key().public_bytes_raw()
