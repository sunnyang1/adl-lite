"""
Tests for Merkle tree batch verification.
"""

import hashlib

import pytest

from adl_lite.key_registry import TransparencyAnchor
from adl_lite.merkle import MerkleTree, compute_chain_merkle_root
from adl_lite.models import Event, EventChain, EventType


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_merkle_root_single_leaf():
    tree = MerkleTree([_h("a")])
    assert tree.root_hex == _h("a")


def test_merkle_root_multiple_leaves():
    leaves = [_h("a"), _h("b"), _h("c")]
    tree = MerkleTree(leaves)
    assert len(tree.root_hex) == 64
    assert tree.root_hex != leaves[0]


def test_inclusion_proof_valid():
    leaves = [_h("a"), _h("b"), _h("c"), _h("d")]
    tree = MerkleTree(leaves)
    for i, leaf in enumerate(leaves):
        proof = tree.proof(i)
        assert proof.leaf_hash == leaf
        assert MerkleTree.verify_proof(proof) is True


def test_inclusion_proof_tampered_leaf_fails():
    leaves = [_h("a"), _h("b"), _h("c")]
    tree = MerkleTree(leaves)
    proof = tree.proof(1)
    proof.leaf_hash = _h("x")
    assert MerkleTree.verify_proof(proof) is False


def test_inclusion_proof_tampered_sibling_fails():
    leaves = [_h("a"), _h("b"), _h("c")]
    tree = MerkleTree(leaves)
    proof = tree.proof(1)
    if proof.siblings:
        sibling_hash, side = proof.siblings[0]
        proof.siblings[0] = (_h("x"), side)
    assert MerkleTree.verify_proof(proof) is False


def test_merkle_tree_requires_leaves():
    with pytest.raises(ValueError):
        MerkleTree([])


def test_proof_index_out_of_range():
    tree = MerkleTree([_h("a"), _h("b")])
    with pytest.raises(IndexError):
        tree.proof(5)


def test_serialize_roundtrip():
    leaves = [_h("a"), _h("b"), _h("c")]
    tree = MerkleTree(leaves)
    data = tree.to_dict()
    restored = MerkleTree.from_dict(data)
    assert restored.root_hex == tree.root_hex
    assert restored.proof(1).root == tree.root_hex


def test_compute_chain_merkle_root():
    leaves = [_h("a"), _h("b")]
    root = compute_chain_merkle_root(leaves)
    assert root == MerkleTree(leaves).root_hex


def test_from_dict_rejects_tampered_root():
    leaves = [_h("a"), _h("b"), _h("c")]
    tree = MerkleTree(leaves)
    data = tree.to_dict()
    data["root"] = _h("tampered")
    with pytest.raises(ValueError, match="Serialized Merkle root does not match"):
        MerkleTree.from_dict(data)


# ---------------------------------------------------------------------------
# F18: Merkle batch verification tests
# ---------------------------------------------------------------------------


def _make_chain(concept_id: str) -> EventChain:
    """Create a minimal EventChain with one REGISTER event."""
    chain = EventChain(concept_id=concept_id)
    chain.append(Event(concept_id=concept_id, event_type=EventType.REGISTER))
    return chain


def _chain_summary(chain: EventChain) -> str:
    """Compute the chain summary hash (same as TransparencyAnchor._chain_summary_hash)."""
    return hashlib.sha256("".join(e.hash for e in chain.events).encode("utf-8")).hexdigest()


def test_merkle_verify_batch_all_valid():
    """5 chains, all with valid proofs → all True."""
    chains = [_make_chain(f"concept_{i}") for i in range(5)]
    leaves = [_chain_summary(c) for c in chains]
    tree = MerkleTree(leaves)
    proofs = {c.concept_id: tree.proof(i) for i, c in enumerate(chains)}

    result = TransparencyAnchor.verify_batch(chains, tree.root_hex, proofs)
    assert result == {c.concept_id: True for c in chains}


def test_merkle_verify_batch_one_tampered():
    """5 chains, tamper 1 chain's event → only that one False."""
    chains = [_make_chain(f"concept_{i}") for i in range(5)]
    leaves = [_chain_summary(c) for c in chains]
    tree = MerkleTree(leaves)
    proofs = {c.concept_id: tree.proof(i) for i, c in enumerate(chains)}

    # Tamper chains[2] by adding a second event
    chains[2].append(Event(concept_id="concept_2", event_type=EventType.VALIDATE))

    result = TransparencyAnchor.verify_batch(chains, tree.root_hex, proofs)
    assert result["concept_0"] is True
    assert result["concept_1"] is True
    assert result["concept_2"] is False
    assert result["concept_3"] is True
    assert result["concept_4"] is True


def test_merkle_verify_batch_missing_proof():
    """Chain with no proof in dict → False."""
    chains = [_make_chain(f"concept_{i}") for i in range(3)]
    leaves = [_chain_summary(c) for c in chains]
    tree = MerkleTree(leaves)
    # Only include proofs for concept_0 and concept_1 — concept_2 is missing
    proofs = {
        chains[0].concept_id: tree.proof(0),
        chains[1].concept_id: tree.proof(1),
    }

    result = TransparencyAnchor.verify_batch(chains, tree.root_hex, proofs)
    assert result["concept_0"] is True
    assert result["concept_1"] is True
    assert result["concept_2"] is False


def test_merkle_verify_batch_wrong_root():
    """Proofs valid but root mismatch → all False."""
    chains = [_make_chain(f"concept_{i}") for i in range(3)]
    leaves = [_chain_summary(c) for c in chains]
    tree = MerkleTree(leaves)
    proofs = {c.concept_id: tree.proof(i) for i, c in enumerate(chains)}

    # Use a different (wrong) merkle root
    wrong_root = _h("wrong_root")

    result = TransparencyAnchor.verify_batch(chains, wrong_root, proofs)
    assert result == {c.concept_id: False for c in chains}


def test_merkle_verify_batch_empty():
    """Empty chains list → empty dict."""
    result = TransparencyAnchor.verify_batch([], _h("any"), {})
    assert result == {}
