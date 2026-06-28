"""
Extended tests for adl_lite.key_registry — Git signature round-trip, Merkle anchors,
and edge cases not covered by tests/test_key_registry.py.
"""

from __future__ import annotations

import hashlib
import warnings

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from adl_lite.key_registry import GitSignatureVerifier, KeyRegistry, TransparencyAnchor
from adl_lite.models import Event, EventChain, EventType


def _make_chain(concept_id: str, count: int = 2) -> EventChain:
    """Helper: create an EventChain with *count* events."""
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


class TestGitSignatureFullFlow:
    """Test the full sign → verify round-trip for GitSignatureVerifier."""

    def test_git_signature_verify_event_not_in_git_history(self, tmp_path):
        """Event not found in git history should warn and return False."""
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        private_key = ed25519.Ed25519PrivateKey.generate()
        registry.register("alice", private_key.public_key())
        verifier = GitSignatureVerifier(registry)

        event = Event(
            concept_id="test-cid",
            event_type=EventType.REGISTER,
            actor="alice",
            payload={"confidence": 0.5},
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = verifier.verify_event(event, repo_path=str(tmp_path))

        assert result is False
        assert any("not found in Git history" in str(warning.message) for warning in w)

    def test_git_signature_verify_event_with_missing_actor(self, tmp_path):
        """Actor not in registry should make verify_event return False."""
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        verifier = GitSignatureVerifier(registry)

        event = Event(
            concept_id="test-cid",
            event_type=EventType.REGISTER,
            actor="unknown_actor",
            payload={"confidence": 0.5},
        )
        # Even if the event were in git history, the actor's key would be missing
        result = verifier.verify_event(event, repo_path=str(tmp_path))
        assert result is False

    def test_git_signature_verify_all_events_in_chain(self, tmp_path):
        """verify_all_events_in_chain should return list of (event, bool) tuples."""
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        verifier = GitSignatureVerifier(registry)

        chain = _make_chain("chain-test", 3)
        results = verifier.verify_all_events_in_chain(chain)
        assert len(results) == 3
        # All should be False since no git history exists
        assert all(is_ok is False for _, is_ok in results)


class TestKeyRegistryDidResolution:
    """Test DID-based key resolution in KeyRegistry."""

    def test_verify_signature_with_did_key(self, tmp_path):
        """Verify signature using did:key method via KeyRegistry."""
        from adl_lite.did_resolver import create_did_key

        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        private_key = ed25519.Ed25519PrivateKey.generate()
        did = create_did_key(private_key.public_key())
        message = b"hello from did:key"
        signature = private_key.sign(message)

        # KeyRegistry.verify_signature dispatches to verify_did_signature for DIDs
        assert registry.verify_signature(did, message, signature) is True

    def test_verify_signature_with_did_key_invalid_sig(self, tmp_path):
        """Verify DID-based signature with wrong key returns False."""
        from adl_lite.did_resolver import create_did_key

        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        private_key = ed25519.Ed25519PrivateKey.generate()
        did = create_did_key(private_key.public_key())
        message = b"hello from did:key"
        bad_signature = b"\x00" * 64

        assert registry.verify_signature(did, message, bad_signature) is False

    def test_get_public_key_for_did(self, tmp_path):
        """get_public_key should resolve DID and return Ed25519 key."""
        from adl_lite.did_resolver import create_did_key

        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        private_key = ed25519.Ed25519PrivateKey.generate()
        did = create_did_key(private_key.public_key())

        retrieved = registry.get_public_key(did)
        assert retrieved is not None
        assert retrieved.public_bytes_raw() == private_key.public_key().public_bytes_raw()

    def test_list_actors_empty_registry(self, tmp_path):
        """Empty registry should return empty list."""
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        assert registry.list_actors() == []


class TestMerkleTransparencyAnchor:
    """Test Merkle-mode transparency anchors and inclusion proofs."""

    def test_merkle_anchor_with_multiple_chains(self, tmp_path):
        """Merkle anchor with multiple chains should produce valid root hash."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [_make_chain("c1"), _make_chain("c2"), _make_chain("c3")]
        value = anchor.anchor(chains, use_merkle=True)
        assert len(value) == 64  # SHA-256 hex digest length
        assert anchor._last_tree is not None
        assert anchor._last_tree.root_hex == value

    def test_merkle_compute_anchor_with_empty_chains(self, tmp_path):
        """compute_anchor with empty chains list should produce a deterministic hash."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        # Empty chains produce a SHA-256 of empty string join
        value = anchor.anchor([], use_merkle=False)
        assert len(value) == 64
        # The value should be SHA-256 of "" (empty concatenation)
        assert value == hashlib.sha256(b"").hexdigest()

    def test_merkle_anchor_empty_with_merkle(self, tmp_path):
        """Merkle anchor with empty chains should use placeholder zero hash."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        value = anchor.anchor([], use_merkle=True)
        assert len(value) == 64
        # The Merkle tree with a single placeholder leaf
        assert anchor._last_tree is not None

    def test_merkle_prove_inclusion(self, tmp_path):
        """prove_inclusion should return valid proof for anchored chain."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [_make_chain("c1"), _make_chain("c2")]
        anchor.anchor(chains, use_merkle=True)

        proof = anchor.prove_inclusion(chains[0])
        assert proof is not None
        assert proof.root == anchor._last_tree.root_hex

        # Verify the proof
        assert anchor.verify_inclusion(chains[0], proof) is True

    def test_merkle_prove_inclusion_missing_chain(self, tmp_path):
        """prove_inclusion for chain not in anchor tree returns None."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [_make_chain("c1")]
        anchor.anchor(chains, use_merkle=True)

        # Create a different chain that was never anchored
        missing_chain = _make_chain("c-missing")
        proof = anchor.prove_inclusion(missing_chain)
        assert proof is None

    def test_merkle_prove_inclusion_no_tree(self, tmp_path):
        """prove_inclusion without prior Merkle anchor returns None."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chain = _make_chain("c1")
        # No anchor computed yet → _last_tree is None
        proof = anchor.prove_inclusion(chain)
        assert proof is None

    def test_merkle_verify_inclusion_wrong_leaf(self, tmp_path):
        """verify_inclusion with mismatched leaf hash returns False."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [_make_chain("c1"), _make_chain("c2")]
        anchor.anchor(chains, use_merkle=True)

        proof = anchor.prove_inclusion(chains[0])
        assert proof is not None

        # Use a different chain for verification (leaf hash mismatch)
        wrong_chain = _make_chain("c-mismatch")
        assert anchor.verify_inclusion(wrong_chain, proof) is False

    def test_merkle_verify_anchor_merkle_vs_flat(self, tmp_path):
        """Verify anchor works for both Merkle and flat formats."""
        chains = [_make_chain("c1"), _make_chain("c2")]

        # Merkle format
        anchor_merkle = TransparencyAnchor(str(tmp_path / "ANCHOR_M.md"))
        anchor_merkle.anchor(chains, use_merkle=True)
        assert anchor_merkle.verify_anchor() is True

        # Flat format (single chain)
        anchor_flat = TransparencyAnchor(str(tmp_path / "ANCHOR_F.md"))
        anchor_flat.anchor([_make_chain("c-flat")], use_merkle=False)
        assert anchor_flat.verify_anchor() is True

    def test_merkle_root_method(self, tmp_path):
        """merkle_root should compute root without writing ANCHOR.md."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [_make_chain("c1"), _make_chain("c2")]
        root = anchor.merkle_root(chains)
        assert len(root) == 64
        # ANCHOR.md should NOT have been created
        assert not (tmp_path / "ANCHOR.md").exists()

    def test_anchor_history_no_git(self, tmp_path):
        """anchor_history without git history returns empty list."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [_make_chain("c1")]
        anchor.anchor(chains)
        # No git commits exist → anchor_history returns empty
        history = anchor.anchor_history()
        assert isinstance(history, list)
        # In a temp dir with no git repo, history is empty
        assert len(history) == 0

    def test_verify_anchor_at_commit_no_git(self, tmp_path):
        """verify_anchor_at_commit without git returns False."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [_make_chain("c1")]
        anchor.anchor(chains)
        result = anchor.verify_anchor_at_commit("abc123")
        assert result is False

    def test_verify_inclusion_valid_proof(self, tmp_path):
        """Full round-trip: anchor → prove → verify_inclusion."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [_make_chain("c1"), _make_chain("c2"), _make_chain("c3")]
        anchor.anchor(chains, use_merkle=True)

        for chain in chains:
            proof = anchor.prove_inclusion(chain)
            assert proof is not None
            assert anchor.verify_inclusion(chain, proof) is True

    def test_verify_anchor_merkle_modified(self, tmp_path):
        """Merkle anchor verification fails when file is tampered."""
        anchor = TransparencyAnchor(str(tmp_path / "ANCHOR.md"))
        chains = [_make_chain("c1")]
        anchor.anchor(chains, use_merkle=True)
        assert anchor.verify_anchor() is True

        # Tamper with the anchor file
        (tmp_path / "ANCHOR.md").write_text("# Bad\n\nRoot: `deadbeef`\n", encoding="utf-8")
        assert anchor.verify_anchor() is False


class TestEd25519KeyLifecycle:
    """Test full Ed25519 key generation, signing, and verification."""

    def test_ed25519_key_generation_and_signing(self):
        """Full Ed25519 lifecycle: generate → sign → verify."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        pk_bytes = public_key.public_bytes_raw()

        assert len(pk_bytes) == 32

        message = b"test message for ed25519"
        signature = private_key.sign(message)
        assert len(signature) == 64

        # Verify with the correct public key
        public_key.verify(signature, message)  # No exception = success

        # Verify with wrong message should raise InvalidSignature
        with pytest.raises(InvalidSignature):
            public_key.verify(signature, b"wrong message")

    def test_key_registry_corrupted_key_data(self, tmp_path):
        """KeyRegistry with corrupted key data should return None for get_public_key."""
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        # Write corrupted data directly
        registry._data["alice"] = {"public_key": "not-valid-base64!!!"}
        registry._save()

        # Reload to test the corruption handling
        registry2 = KeyRegistry(str(tmp_path / "registry.yaml"))
        result = registry2.get_public_key("alice")
        assert result is None

        # verify_signature should also return False
        assert registry2.verify_signature("alice", b"msg", b"sig") is False

    def test_key_registry_verify_signature_wrong_key(self, tmp_path):
        """Sign with key1, verify with key2 → False."""
        registry = KeyRegistry(str(tmp_path / "registry.yaml"))
        key1 = ed25519.Ed25519PrivateKey.generate()
        key2 = ed25519.Ed25519PrivateKey.generate()
        registry.register("alice", key1.public_key())

        message = b"signed by alice"
        signature = key2.sign(message)  # Wrong key!

        assert registry.verify_signature("alice", message, signature) is False
