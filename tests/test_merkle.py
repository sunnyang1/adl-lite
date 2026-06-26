"""
Tests for Merkle tree batch verification.
"""

import hashlib

import pytest

from adl_lite.merkle import MerkleTree, compute_chain_merkle_root


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
