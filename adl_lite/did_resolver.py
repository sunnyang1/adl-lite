"""
DID Resolver for ADL Lite — did:key, did:web, did:ethr.

Design:
  - did:key  : local Ed25519 multibase parsing (zero external deps).
  - did:web  : HTTPS fetch of /.well-known/did.json; supports Ed25519/secp256k1/JWK.
  - did:ethr : Ethereum ethr-did registry resolver; secp256k1 recovery (optional web3.py).
  - All non-stdlib crypto dependencies are optional; missing deps raise ImportError only
    when the corresponding method is actually invoked.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.parse
import urllib.request
import warnings
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519

# Ed25519 multicodec prefix (0xed01) as varint
ED25519_MULTICODEC_PREFIX = bytes([0xED, 0x01])

DID_METHODS = ("key", "web", "ethr")


@dataclass
class VerificationMethod:
    """A W3C DID verificationMethod entry normalized for ADL Lite."""

    id: str
    type: str
    controller: str
    public_key_bytes: bytes
    format: str  # 'multibase', 'jwk', 'hex', 'base64', 'address'
    address: str | None = None  # For blockchain recovery methods (e.g., did:ethr)


@dataclass
class DIDDocument:
    """Normalized DID document."""

    id: str
    verification_methods: list[VerificationMethod] = field(default_factory=list)
    assertion_method: list[str] = field(default_factory=list)

    def key_for_purpose(self, purpose: str = "assertionMethod") -> VerificationMethod | None:
        """Return the first verification method usable for *purpose*."""
        ids = self.assertion_method if purpose == "assertionMethod" else []
        if not ids:
            ids = [vm.id for vm in self.verification_methods]
        by_id = {vm.id: vm for vm in self.verification_methods}
        for vm_id in ids:
            vm = by_id.get(vm_id)
            if vm:
                return vm
        return None


# ---------------------------------------------------------------------------
# Base58btc helpers (kept for did:key)
# ---------------------------------------------------------------------------


def _base58btc_decode(s: str) -> bytes:
    """Decode a base58btc string (Bitcoin alphabet) to bytes."""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    base = len(alphabet)
    num_leading_zeros = 0
    for ch in s:
        if ch == "1":
            num_leading_zeros += 1
        else:
            break
    num = 0
    for ch in s:
        num = num * base + alphabet.index(ch)
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


# ---------------------------------------------------------------------------
# did:key
# ---------------------------------------------------------------------------


def resolve_did_key(did: str, **_kwargs: Any) -> DIDDocument:
    """
    Resolve a did:key DID to a DIDDocument wrapping an Ed25519 public key.

    Raises:
        ValueError: if the DID is malformed or not a did:key
    """
    if not did.startswith("did:key:"):
        raise ValueError(f"Only did:key is supported; got {did}")

    match = re.match(r"did:key:z([a-km-zA-HJ-NP-Z1-9]+)", did)
    if not match:
        raise ValueError(f"Invalid did:key format: {did}")

    multibase = match.group(1)
    raw_bytes = _base58btc_decode(multibase)

    if not raw_bytes.startswith(ED25519_MULTICODEC_PREFIX):
        raise ValueError(
            f"Unexpected multicodec prefix: expected {ED25519_MULTICODEC_PREFIX.hex()}, "
            f"got {raw_bytes[: len(ED25519_MULTICODEC_PREFIX)].hex()}"
        )

    pub_key_bytes = raw_bytes[len(ED25519_MULTICODEC_PREFIX) :]
    if len(pub_key_bytes) != 32:
        raise ValueError(f"Expected 32-byte Ed25519 public key, got {len(pub_key_bytes)} bytes")

    return DIDDocument(
        id=did,
        verification_methods=[
            VerificationMethod(
                id=f"{did}#{did.split(':')[-1]}",
                type="Ed25519VerificationKey2020",
                controller=did,
                public_key_bytes=pub_key_bytes,
                format="multibase",
            )
        ],
        assertion_method=[f"{did}#{did.split(':')[-1]}"],
    )


def _ed25519_public_key_from_doc(doc: DIDDocument) -> ed25519.Ed25519PublicKey:
    vm = doc.key_for_purpose("assertionMethod")
    if vm is None or vm.type not in ("Ed25519VerificationKey2020", "Ed25519VerificationKey2018"):
        raise ValueError("DID document has no usable Ed25519 assertion method")
    return ed25519.Ed25519PublicKey.from_public_bytes(vm.public_key_bytes)


def create_did_key(public_key: ed25519.Ed25519PublicKey) -> str:
    """Create a did:key DID from an Ed25519 public key."""
    pub_key_bytes = public_key.public_bytes_raw()
    raw_bytes = ED25519_MULTICODEC_PREFIX + pub_key_bytes
    multibase = _base58btc_encode(raw_bytes)
    return f"did:key:z{multibase}"


# ---------------------------------------------------------------------------
# did:web
# ---------------------------------------------------------------------------


def _parse_did_web(did: str) -> str:
    """Convert did:web:example.com:path to https://example.com/path/.well-known/did.json.

    Per W3C DID spec, port numbers are represented by percent-encoding the colon
    as %3A (e.g. did:web:example.com%3A8080 → https://example.com:8080/.well-known/did.json).
    """
    if not did.startswith("did:web:"):
        raise ValueError(f"Not a did:web: {did}")
    encoded = did[len("did:web:") :]
    decoded = urllib.parse.unquote(encoded)
    parts = decoded.split(":")
    domain = parts[0]
    # W3C DID spec: if the second segment looks like a port number
    # (all digits), treat it as a port, not a path component
    port: str | None = None
    if len(parts) > 1 and parts[1].isdigit():
        port = parts[1]
        path_parts = parts[2:]
    else:
        path_parts = parts[1:]
    path = "/".join(path_parts) if path_parts else ""
    host = f"{domain}:{port}" if port else domain
    if path:
        url = f"https://{host}/{path}/did.json"
    else:
        url = f"https://{host}/.well-known/did.json"
    return url


def _decode_jwk(jwk: dict[str, Any]) -> bytes:
    """Decode a public-key JWK to raw bytes for Ed25519 or secp256k1."""
    kty = jwk.get("kty")
    crv = jwk.get("crv")
    if kty == "OKP" and crv == "Ed25519":
        return base64.urlsafe_b64decode(jwk["x"] + "===")
    if kty == "EC" and crv == "secp256k1":
        x = base64.urlsafe_b64decode(jwk["x"] + "===")
        y = base64.urlsafe_b64decode(jwk["y"] + "===")
        # Uncompressed SEC1: 0x04 || x || y
        return b"\x04" + x + y
    raise ValueError(f"Unsupported JWK: kty={kty}, crv={crv}")


def _vm_from_did_doc_entry(entry: dict[str, Any], controller: str) -> VerificationMethod | None:
    vtype = entry.get("type", "")
    vm_id = entry.get("id", "")
    public_key_bytes: bytes | None = None
    fmt = "unknown"

    if "publicKeyMultibase" in entry:
        encoded = entry["publicKeyMultibase"]
        if encoded.startswith("z"):
            raw = _base58btc_decode(encoded[1:])
            if raw.startswith(ED25519_MULTICODEC_PREFIX):
                public_key_bytes = raw[len(ED25519_MULTICODEC_PREFIX) :]
                fmt = "multibase"
            elif raw.startswith(bytes([0xE7, 0x01])):  # secp256k1-pub
                public_key_bytes = raw[2:]
                fmt = "multibase"
    elif "publicKeyJwk" in entry:
        public_key_bytes = _decode_jwk(entry["publicKeyJwk"])
        fmt = "jwk"
    elif "publicKeyBase58" in entry:
        public_key_bytes = _base58btc_decode(entry["publicKeyBase58"])
        fmt = "base58"
    elif "publicKeyHex" in entry:
        public_key_bytes = bytes.fromhex(entry["publicKeyHex"])
        fmt = "hex"

    if public_key_bytes is None:
        return None
    return VerificationMethod(
        id=vm_id,
        type=vtype,
        controller=controller,
        public_key_bytes=public_key_bytes,
        format=fmt,
    )


def resolve_did_web(did: str, timeout: int = 10, **_kwargs: Any) -> DIDDocument:
    """
    Resolve a did:web DID by fetching its DID document over HTTPS.

    Raises:
        ValueError: on malformed DID or unsupported document.
        RuntimeError: on network failure.
    """
    url = _parse_did_web(did)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch did:web document from {url}: {exc}") from exc

    if doc.get("id") != did:
        raise ValueError("DID document id does not match requested DID")

    controller = doc.get("id", did)
    vms = []
    for entry in doc.get("verificationMethod", []):
        vm = _vm_from_did_doc_entry(entry, controller)
        if vm:
            vms.append(vm)

    assertion = doc.get("assertionMethod", [])
    if isinstance(assertion, dict):
        assertion = [assertion.get("id", "")]
    elif isinstance(assertion, list):
        assertion = [m.get("id", m) if isinstance(m, dict) else m for m in assertion]

    if not vms:
        raise ValueError("did:web document contains no supported verification methods")

    return DIDDocument(id=did, verification_methods=vms, assertion_method=assertion)


# ---------------------------------------------------------------------------
# did:ethr
# ---------------------------------------------------------------------------


def _require_eth() -> Any:
    try:
        import eth_account  # noqa: F401
        import web3  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "did:ethr support requires optional dependencies: pip install adl-lite[did]"
        ) from exc
    return web3, eth_account


def resolve_did_ethr(did: str, rpc_url: str | None = None, **_kwargs: Any) -> DIDDocument:
    """
    Resolve a did:ethr DID by reading the Ethereum registry events.

    MVP status (Phase 1): **resolution only**. This is a minimal implementation:
    it expects the DID to encode an Ethereum address (did:ethr:<address> or
    did:ethr:<chain-id>:<address>) and derives the secp256k1 public key from
    known delegate events when possible. Key recovery is NOT supported in
    Phase 1 — the returned verification method carries the address with empty
    ``public_key_bytes``, and ``trust_model`` validation explicitly rejects
    did:ethr actors (``ADLUnsupportedDIDMethodError``).

    For direct address-only DIDs, the public key is not recoverable from the
    address alone; callers should supply a known delegate or rely on signatures
    verified via ``verify_did_signature`` with secp256k1 recovery.

    Optional dependency: web3.py, eth-account (``pip install adl-lite[did]``).
    """
    web3, _ = _require_eth()

    if not did.startswith("did:ethr:"):
        raise ValueError(f"Not a did:ethr: {did}")

    rest = did[len("did:ethr:") :]
    parts = rest.split(":")
    if len(parts) == 1:
        address = parts[0]
    else:
        _ = int(parts[0])  # chain-id present; currently unused in MVP resolver
        address = parts[1]

    if not re.fullmatch(r"0x[a-fA-F0-9]{40}", address):
        raise ValueError(f"Invalid Ethereum address in did:ethr: {did}")

    # Direct address resolution cannot recover the public key, but we can still
    # construct a document whose verification method carries the address. The
    # actual public key bytes are left empty; signature verification uses
    # ecrecover on the message/signature.
    vm_id = f"{did}#owner"
    vm = VerificationMethod(
        id=vm_id,
        type="EcdsaSecp256k1RecoveryMethod2020",
        controller=did,
        public_key_bytes=b"",
        format="address",
        address=address,
    )

    # Attempt to enrich via registry if rpc_url is provided (best-effort).
    if rpc_url:
        try:
            w3 = web3.Web3(web3.Web3.HTTPProvider(rpc_url))
            # Minimal ethr-did registry address on mainnet; network-specific overrides possible.
            registry = w3.eth.contract(
                address=web3.Web3.to_checksum_address("0xEcf7D892B626c811127A23e6127E7Fb8Cb07F31e"),
                abi=_ETHR_REGISTRY_ABI,
            )
            # Fetch owner to confirm; public-key recovery from delegate events is complex
            # and omitted in this MVP to keep dependency surface small.
            owner = registry.functions.identityOwner(address).call()
            if owner.lower() != address.lower():
                warnings.warn(f"did:ethr owner mismatch: {owner} vs {address}", stacklevel=2)
        except Exception as exc:
            warnings.warn(f"did:ethr registry lookup failed: {exc}", stacklevel=2)

    return DIDDocument(id=did, verification_methods=[vm], assertion_method=[vm_id])


# Minimal ethr-did registry ABI fragment for identityOwner only.
_ETHR_REGISTRY_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "identity", "type": "address"}],
        "name": "identityOwner",
        "outputs": [{"name": "", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    }
]


# ---------------------------------------------------------------------------
# Multiplexer
# ---------------------------------------------------------------------------


class DIDResolver:
    """Multi-method DID resolver with method dispatch."""

    def __init__(self) -> None:
        self._resolvers: dict[str, Any] = {
            "key": resolve_did_key,
            "web": resolve_did_web,
            "ethr": resolve_did_ethr,
        }

    def resolve(self, did: str, **kwargs: Any) -> DIDDocument:
        """Resolve *did* and return a normalized DIDDocument."""
        method = self._method(did)
        resolver = self._resolvers.get(method)
        if resolver is None:
            raise ValueError(f"Unsupported DID method: {method}")
        return resolver(did, **kwargs)  # type: ignore[no-any-return]

    def register(self, method: str, resolver: Any) -> None:
        """Register or override a method resolver."""
        self._resolvers[method] = resolver

    @staticmethod
    def _method(did: str) -> str:
        if not did.startswith("did:"):
            raise ValueError(f"Not a DID: {did}")
        parts = did.split(":")
        if len(parts) < 3:
            raise ValueError(f"Malformed DID: {did}")
        return parts[1]


# Global default resolver instance.
default_resolver = DIDResolver()


def resolve_did(did: str, **kwargs: Any) -> DIDDocument:
    """Convenience resolve using the default resolver."""
    return default_resolver.resolve(did, **kwargs)


def is_did(actor: str) -> bool:
    """Return True if *actor* looks like a supported DID."""
    if not isinstance(actor, str) or not actor.startswith("did:"):
        return False
    parts = actor.split(":")
    return len(parts) >= 3 and parts[1] in DID_METHODS


def verify_did_signature(
    did: str,
    message: bytes,
    signature: bytes,
    *,
    rpc_url: str | None = None,
) -> bool:
    """
    Verify a signature using the public key resolved from *did*.

    For did:ethr, *signature* must be a 65-byte recoverable signature
    (r || s || v) and the public key is recovered via ecrecover.
    """
    method = DIDResolver._method(did)
    try:
        if method == "key":
            doc = resolve_did_key(did)
            pk = _ed25519_public_key_from_doc(doc)
            pk.verify(signature, message)
            return True
        if method == "web":
            doc = resolve_did_web(did)
            vm = doc.key_for_purpose("assertionMethod")
            if vm is None:
                return False
            if vm.type in ("Ed25519VerificationKey2020", "Ed25519VerificationKey2018"):
                pk = ed25519.Ed25519PublicKey.from_public_bytes(vm.public_key_bytes)
                pk.verify(signature, message)
                return True
            if vm.type in (
                "EcdsaSecp256k1VerificationKey2019",
                "EcdsaSecp256k1RecoveryMethod2020",
            ):
                return _verify_secp256k1_signature(vm.public_key_bytes, message, signature)
            return False
        if method == "ethr":
            return _verify_ethr_signature(did, message, signature, rpc_url=rpc_url)
    except Exception:
        return False
    return False


def _verify_secp256k1_signature(public_key_bytes: bytes, message: bytes, signature: bytes) -> bool:
    """Verify a non-recoverable secp256k1 signature (64 bytes r||s)."""
    try:
        import coincurve

        if len(signature) == 65:
            signature = signature[:64]
        return bool(coincurve.PublicKey(public_key_bytes).verify(signature, message))
    except ImportError:
        pass
    try:
        import ecdsa

        vk = ecdsa.VerifyingKey.from_string(public_key_bytes, curve=ecdsa.SECP256k1)
        if len(signature) == 65:
            signature = signature[:64]
        return bool(vk.verify(signature, message, hashfunc=hashlib.sha256))
    except ImportError:
        pass
    raise ImportError(
        "secp256k1 signature verification requires coincurve or ecdsa: pip install adl-lite[did]"
    )


def _verify_ethr_signature(
    did: str, message: bytes, signature: bytes, rpc_url: str | None = None
) -> bool:
    """Verify a did:ethr signature using ecrecover."""
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except ImportError as exc:
        raise ImportError(
            "did:ethr signature verification requires eth-account: pip install adl-lite[did]"
        ) from exc

    if len(signature) != 65:
        return False

    address = did.split(":")[-1]
    if not re.fullmatch(r"0x[a-fA-F0-9]{40}", address):
        return False

    try:
        encoded = encode_defunct(message)
        recovered = Account.recover_message(encoded, signature=signature)
        return bool(recovered.lower() == address.lower())
    except Exception:
        return False
