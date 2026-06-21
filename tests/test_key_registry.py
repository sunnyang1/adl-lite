"""
Tests for adl_lite.key_registry — Ed25519 key registry, Git verifier, and transparency anchor.
"""

from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from adl_lite.key_registry import (
    GitSignatureVerifier,
    KeyRegistry,
    TransparencyAnchor,
)
from adl_lite.models import Event, EventChain, EventType


class TestKeyRegistry:
    def test_register_and_verify_signature(self, tmp_path):
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        registry.register("alice", public_key)
        message = b"hello world"
        signature = private_key.sign(message)

        assert registry.verify_signature("alice", message, signature) is True
        assert registry.list_actors() == ["alice"]

    def test_revoke_and_verify_fails(self, tmp_path):
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        registry.register("alice", public_key)
        registry.revoke("alice")
        message = b"hello world"
        signature = private_key.sign(message)

        assert registry.is_revoked("alice") is True
        assert registry.verify_signature("alice", message, signature) is False

    def test_unknown_actor_verify_fails(self, tmp_path):
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        message = b"hello world"
        signature = b"fake signature"

        assert registry.verify_signature("bob", message, signature) is False

    def test_revoke_unknown_actor_raises(self, tmp_path):
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        with pytest.raises(KeyError, match="not registered"):
            registry.revoke("alice")

    def test_get_public_key_roundtrip(self, tmp_path):
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        registry.register("alice", public_key)
        retrieved = registry.get_public_key("alice")
        assert retrieved is not None
        assert base64.b64encode(retrieved.public_bytes_raw()) == base64.b64encode(
            public_key.public_bytes_raw()
        )


class TestTransparencyAnchor:
    def _make_chain(self, concept_id: str, count: int = 2) -> EventChain:
        chain = EventChain(concept_id=concept_id)
        for i in range(count):
            chain.append(
                Event(
                    concept_id=concept_id,
                    event_type=EventType.REGISTER if i == 0 else EventType.VALIDATE,
                    actor="agent",
                    payload={"confidence": 0.5},
                )
            )
        return chain

    def test_anchor_is_deterministic(self, tmp_path):
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [self._make_chain("c1"), self._make_chain("c2")]
        v1 = anchor.anchor(chains)
        v2 = anchor.anchor(chains)
        assert v1 == v2

    def test_verify_anchor_passes(self, tmp_path):
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [self._make_chain("c1")]
        anchor.anchor(chains)
        assert anchor.verify_anchor() is True

    def test_verify_anchor_fails_when_modified(self, tmp_path):
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [self._make_chain("c1")]
        anchor.anchor(chains)
        (tmp_path / "ANCHOR.md").write_text("# Bad\n\n`deadbeef`\n", encoding="utf-8")
        assert anchor.verify_anchor() is False

    def test_verify_anchor_fails_when_missing(self, tmp_path):
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [self._make_chain("c1")]
        anchor.anchor(chains)
        (tmp_path / "ANCHOR.md").unlink()
        assert anchor.verify_anchor() is False


class TestGitSignatureVerifier:
    def test_verify_commit_with_missing_key(self, tmp_path):
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        verifier = GitSignatureVerifier(registry)
        # Actor not registered → should return False
        assert verifier.verify_commit_signature("alice", "HEAD") is False

    def test_verify_commit_with_registered_key_no_git(self, tmp_path):
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        private_key = ed25519.Ed25519PrivateKey.generate()
        registry.register("alice", private_key.public_key())
        verifier = GitSignatureVerifier(registry)
        # Even with key registered, HEAD is unlikely to verify in this repo
        result = verifier.verify_commit_signature("alice", "HEAD")
        # Result is either False (unsigned repo) or True (signed repo) —
        # we only assert it doesn't raise.
        assert isinstance(result, bool)
