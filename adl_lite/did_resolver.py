"""
Minimal DID Resolver for ADL Lite — did:key only (local, no network).

This implements the smallest viable DID layer to respond to reviewer Q2
(authentication beyond self-declared strings). did:key is chosen because:
  - Zero external dependencies (no HTTP, no blockchain)
  - Ed25519 public key is embedded directly in the DID string
  - Pure local parsing: base58btc decode → public key bytes

Full DID integration (did:web, did:ethr, LD-Proofs, Merkle trees) remains
future work (FW4). This module provides the minimal scaffolding that
demonstrates the design intent and enables single-event signature
verification using DID-derived keys.
"""

from __future__ import annotations

import re

from cryptography.hazmat.primitives.asymmetric import ed25519

# Ed25519 multicodec prefix (0xed01) as varint
ED25519_MULTICODEC_PREFIX = bytes([0xed, 0x01])


def _base58btc_decode(s: str) -> bytes:
    """Decode a base58btc string (Bitcoin alphabet) to bytes."""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    base = len(alphabet)
    # Leading zeros
    num_leading_zeros = 0
    for ch in s:
        if ch == "1":
            num_leading_zeros += 1
        else:
            break
    # Convert to integer
    num = 0
    for ch in s:
        num = num * base + alphabet.index(ch)
    # Convert to bytes
    result = num.to_bytes((num.bit_length() + 7) // 8, "big")
    return b"\x00" * num_leading_zeros + result


def _base58btc_encode(data: bytes) -> str:
    """Encode bytes to base58btc string."""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    base = len(alphabet)
    num = int.from_bytes(data, "big")
    if num == 0:
        return "1" * len(data)
    result = ""
    while num > 0:
        num, rem = divmod(num, base)
        result = alphabet[rem] + result
    leading_zeros = len(data) - len(data.lstrip(b"\x00"))
    return "1" * leading_zeros + result


def resolve_did_key(did: str) -> ed25519.Ed25519PublicKey:
    """
    Resolve a did:key DID to an Ed25519 public key.

    did:key format: did:key:z<multibase(base58btc, multicodec(ed25519-pub, 32-byte-pubkey))>

    Example: did:key:z6MkqRYqQiSgvZQdnBytw86Qbs2ZWUkGf22dMoR4K25eNu6q

    Raises:
        ValueError: if the DID is malformed or not a did:key
    """
    if not did.startswith("did:key:"):
        raise ValueError(f"Only did:key is supported; got {did}")

    # Extract the multibase string after "did:key:z"
    match = re.match(r"did:key:z([a-km-zA-HJ-NP-Z1-9]+)", did)
    if not match:
        raise ValueError(f"Invalid did:key format: {did}")

    multibase = match.group(1)
    raw_bytes = _base58btc_decode(multibase)

    # Verify multicodec prefix
    if not raw_bytes.startswith(ED25519_MULTICODEC_PREFIX):
        raise ValueError(
            f"Unexpected multicodec prefix: expected {ED25519_MULTICODEC_PREFIX.hex()}, "
            f"got {raw_bytes[:len(ED25519_MULTICODEC_PREFIX)].hex()}"
        )

    pub_key_bytes = raw_bytes[len(ED25519_MULTICODEC_PREFIX):]
    if len(pub_key_bytes) != 32:
        raise ValueError(f"Expected 32-byte Ed25519 public key, got {len(pub_key_bytes)} bytes")

    return ed25519.Ed25519PublicKey.from_public_bytes(pub_key_bytes)


def create_did_key(public_key: ed25519.Ed25519PublicKey) -> str:
    """
    Create a did:key DID from an Ed25519 public key.

    This is the inverse of resolve_did_key().
    """
    pub_key_bytes = public_key.public_bytes_raw()
    raw_bytes = ED25519_MULTICODEC_PREFIX + pub_key_bytes
    multibase = _base58btc_encode(raw_bytes)
    return f"did:key:z{multibase}"


def is_did(actor: str) -> bool:
    """Return True if the actor string is a DID (did:key only)."""
    return actor.startswith("did:key:")


def verify_did_signature(
    did: str, message: bytes, signature: bytes
) -> bool:
    """
    Verify a message signature using the public key resolved from a did:key.

    Args:
        did: The did:key DID of the signer
        message: The message that was signed
        signature: The Ed25519 signature bytes

    Returns:
        True if the signature is valid, False otherwise
    """
    try:
        pk = resolve_did_key(did)
        pk.verify(signature, message)
        return True
    except Exception:
        return False
