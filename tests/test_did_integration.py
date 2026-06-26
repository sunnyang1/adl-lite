"""
Tests for DID integration (did:key, did:web, did:ethr) and LD-Proofs.
"""

import base64
import json
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from adl_lite.did_resolver import (
    DIDDocument,
    DIDResolver,
    create_did_key,
    is_did,
    resolve_did,
    resolve_did_key,
    resolve_did_web,
    verify_did_signature,
)
from adl_lite.key_registry import KeyRegistry
from adl_lite.ld_proof import create_event_proof, verify_event_proof
from adl_lite.models import Event, EventChain, EventType

# ---------------------------------------------------------------------------
# did:key resolution tests
# ---------------------------------------------------------------------------


def test_create_and_resolve_did_key():
    """Round-trip: create did:key from key → resolve to DIDDocument."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    did = create_did_key(public_key)
    assert did.startswith("did:key:z")
    doc = resolve_did_key(did)
    assert isinstance(doc, DIDDocument)
    assert doc.id == did
    vm = doc.key_for_purpose("assertionMethod")
    assert vm is not None
    assert vm.public_key_bytes == public_key.public_bytes_raw()


def test_resolve_did_key_invalid_prefix():
    with pytest.raises(ValueError, match="Only did:key"):
        resolve_did_key("did:web:example.com")


def test_is_did():
    assert is_did("did:key:z6MkqRY") is True
    assert is_did("agent_1") is False
    assert is_did("did:web:example.com") is True
    assert is_did("did:ethr:0x1234567890123456789012345678901234567890") is True


# ---------------------------------------------------------------------------
# did:web resolution tests
# ---------------------------------------------------------------------------


SAMPLE_DID_WEB_DOC = {
    "@context": "https://www.w3.org/ns/did/v1",
    "id": "did:web:example.com",
    "verificationMethod": [
        {
            "id": "did:web:example.com#key-1",
            "type": "Ed25519VerificationKey2020",
            "controller": "did:web:example.com",
            "publicKeyJwk": {
                "kty": "OKP",
                "crv": "Ed25519",
                "x": "",  # filled below
            },
        }
    ],
    "assertionMethod": ["did:web:example.com#key-1"],
}


def test_resolve_did_web_with_jwk():
    private_key = ed25519.Ed25519PrivateKey.generate()
    pub_bytes = private_key.public_key().public_bytes_raw()
    jwk_x = base64.urlsafe_b64encode(pub_bytes).decode("ascii").rstrip("=")

    doc_json = json.loads(json.dumps(SAMPLE_DID_WEB_DOC))
    doc_json["verificationMethod"][0]["publicKeyJwk"]["x"] = jwk_x

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = mock_urlopen.return_value.__enter__.return_value
        mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
        doc = resolve_did_web("did:web:example.com")

    assert doc.id == "did:web:example.com"
    vm = doc.key_for_purpose("assertionMethod")
    assert vm is not None
    assert vm.public_key_bytes == pub_bytes


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
# DID resolver multiplexer tests
# ---------------------------------------------------------------------------


def test_default_resolver_dispatch():
    resolver = DIDResolver()
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    doc = resolver.resolve(did)
    assert doc.id == did


def test_resolve_did_convenience():
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    doc = resolve_did(did)
    assert doc.id == did


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
# LD-Proof tests
# ---------------------------------------------------------------------------


def test_sign_and_verify_event_proof():
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    event = Event(
        concept_id="test",
        event_type=EventType.VALIDATE,
        actor=did,
        payload={"confidence": 0.8},
    )
    event.proof = create_event_proof(
        event,
        private_key,
        verification_method=f"{did}#{did.split(':')[-1]}",
    )
    assert verify_event_proof(event) is True


def test_event_proof_integrity_in_chain(tmp_path):
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    registry = KeyRegistry(registry_path=tmp_path / "keys.yaml")

    event = Event(
        concept_id="test",
        event_type=EventType.REGISTER,
        actor=did,
    )
    event.proof = create_event_proof(
        event,
        private_key,
        verification_method=f"{did}#{did.split(':')[-1]}",
    )
    chain = EventChain(concept_id="test")
    chain.append(event)
    assert chain.verify_integrity(registry=registry) is True


# ---------------------------------------------------------------------------
# Known test vectors (did:key round-trip)
# ---------------------------------------------------------------------------


def test_known_did_key_vector():
    """Verify that a did:key created by our own implementation round-trips correctly."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    did = create_did_key(private_key.public_key())
    doc = resolve_did_key(did)
    vm = doc.key_for_purpose("assertionMethod")
    assert vm is not None
    assert len(vm.public_key_bytes) == 32
    assert vm.public_key_bytes == private_key.public_key().public_bytes_raw()
