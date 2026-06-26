"""
Merkle tree utilities for ADL Lite batch verification.

Provides SHA-256 Merkle trees over event/chain hashes with inclusion proofs.
Used by TransparencyAnchor for O(log n) batch integrity checks.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class MerkleProof:
    """Inclusion proof for a leaf in a Merkle tree."""

    leaf_index: int
    leaf_hash: str
    siblings: list[tuple[str, str]]  # (sibling_hash, side) where side is 'left' or 'right'
    root: str


def _hash_pair(left: bytes, right: bytes) -> bytes:
    """Hash two child digests as SHA-256(left || right)."""
    return hashlib.sha256(left + right).digest()


class MerkleTree:
    """
    SHA-256 Merkle tree over a list of hex-encoded leaf hashes.

    Example:
        leaves = ["a1b2...", "c3d4...", "e5f6..."]
        tree = MerkleTree(leaves)
        print(tree.root_hex)
        proof = tree.proof(1)
        assert MerkleTree.verify_proof(proof)
    """

    def __init__(self, leaves: list[str]) -> None:
        if not leaves:
            raise ValueError("MerkleTree requires at least one leaf")
        self.leaves: list[str] = leaves
        self._leaf_bytes: list[bytes] = [bytes.fromhex(h) for h in leaves]
        self._levels: list[list[bytes]] = self._build(self._leaf_bytes)

    def _build(self, leaves: list[bytes]) -> list[list[bytes]]:
        levels: list[list[bytes]] = [leaves]
        current = leaves[:]
        while len(current) > 1:
            next_level: list[bytes] = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i + 1] if i + 1 < len(current) else left
                next_level.append(_hash_pair(left, right))
            current = next_level
            levels.append(current)
        return levels

    @property
    def root_hex(self) -> str:
        """Return the Merkle root as a hex string."""
        return self._levels[-1][0].hex()

    def proof(self, index: int) -> MerkleProof:
        """Build an inclusion proof for the leaf at *index*."""
        if not (0 <= index < len(self.leaves)):
            raise IndexError(f"Leaf index {index} out of range")

        siblings: list[tuple[str, str]] = []
        idx = index
        for level in self._levels[:-1]:
            if idx % 2 == 0:
                sibling_idx = idx + 1
                side = "right"
            else:
                sibling_idx = idx - 1
                side = "left"
            if sibling_idx < len(level):
                sibling_hash = level[sibling_idx].hex()
            else:
                # Odd-length level: sibling is the same node (duplicated in hashing)
                sibling_hash = level[idx].hex()
                side = "right"
            siblings.append((sibling_hash, side))
            idx //= 2

        return MerkleProof(
            leaf_index=index,
            leaf_hash=self.leaves[index],
            siblings=siblings,
            root=self.root_hex,
        )

    @staticmethod
    def verify_proof(proof: MerkleProof) -> bool:
        """Verify an inclusion proof against its embedded root."""
        current = bytes.fromhex(proof.leaf_hash)
        for sibling_hash, side in proof.siblings:
            sibling = bytes.fromhex(sibling_hash)
            if side == "left":
                current = _hash_pair(sibling, current)
            else:
                current = _hash_pair(current, sibling)
        return current.hex() == proof.root

    def to_dict(self) -> dict[str, Any]:
        """Serialize tree structure (levels as hex strings)."""
        return {
            "leaves": self.leaves,
            "root": self.root_hex,
            "levels": [[h.hex() for h in level] for level in self._levels],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MerkleTree:
        """Rebuild a MerkleTree from serialized levels and validate consistency."""
        tree = cls.__new__(cls)
        tree.leaves = list(data["leaves"])
        tree._leaf_bytes = [bytes.fromhex(h) for h in tree.leaves]
        # Rebuild levels from leaves to guarantee consistency; reject tampered dumps.
        tree._levels = tree._build(tree._leaf_bytes)
        expected_root = data.get("root")
        if expected_root is not None and tree.root_hex != expected_root:
            raise ValueError("Serialized Merkle root does not match recomputed root")
        return tree


def compute_chain_merkle_root(leaves: list[str]) -> str:
    """Convenience: compute the Merkle root over a list of hex hashes."""
    return MerkleTree(leaves).root_hex
