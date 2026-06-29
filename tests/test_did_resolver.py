"""
Comprehensive tests for adl_lite.did_resolver — all resolution and verification paths.

Covers: base58btc helpers, did:key (valid + all error paths), did:web (parsing,
JWK/multibase/base58/hex formats, error cases), did:ethr (address-only + rpc_url),
DIDResolver multiplexer (register, unsupported, malformed), is_did edge cases,
verify_did_signature (key/web/ethr), _verify_secp256k1_signature,
_verify_ethr_signature, DIDDocument.key_for_purpose.
"""

from __future__ import annotations

import base64
import json
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from adl_lite.did_resolver import (
    ED25519_MULTICODEC_PREFIX,
    DIDDocument,
    DIDResolver,
    VerificationMethod,
    _base58btc_decode,
    _base58btc_encode,
    _decode_jwk,
    _ed25519_public_key_from_doc,
    _parse_did_web,
    _vm_from_did_doc_entry,
    create_did_key,
    is_did,
    resolve_did,
    resolve_did_ethr,
    resolve_did_key,
    resolve_did_web,
    verify_did_signature,
)

# ---------------------------------------------------------------------------
# base58btc helpers
# ---------------------------------------------------------------------------


class TestBase58btc:
    def test_encode_decode_roundtrip(self):
        data = b"\x00\x01\x02\x03\x04hello world"
        encoded = _base58btc_encode(data)
        decoded = _base58btc_decode(encoded)
        assert decoded == data

    def test_encode_empty_bytes(self):
        assert _base58btc_encode(b"") == ""

    def test_encode_all_zeros(self):
        result = _base58btc_encode(b"\x00\x00\x00")
        assert result == "111"

    def test_encode_single_byte(self):
        result = _base58btc_encode(b"\x00")
        assert result == "1"

    def test_decode_empty_string(self):
        # Decoding empty should produce empty bytes
        result = _base58btc_decode("")
        assert result == b""

    def test_decode_leading_zeros(self):
        result = _base58btc_decode("111")
        assert result == b"\x00\x00\x00"

    def test_roundtrip_32_byte_key(self):
        key = bytes(range(32))
        encoded = _base58btc_encode(key)
        decoded = _base58btc_decode(encoded)
        assert decoded == key

    def test_roundtrip_with_multicodec_prefix(self):
        data = ED25519_MULTICODEC_PREFIX + bytes(range(32))
        encoded = _base58btc_encode(data)
        decoded = _base58btc_decode(encoded)
        assert decoded == data


# ---------------------------------------------------------------------------
# did:key resolution — error paths
# ---------------------------------------------------------------------------


class TestResolveDidKeyErrors:
    def test_not_did_key_prefix(self):
        with pytest.raises(ValueError, match="Only did:key"):
            resolve_did_key("did:web:example.com")

    def test_invalid_format_no_z_prefix(self):
        with pytest.raises(ValueError, match="Invalid did:key format"):
            resolve_did_key("did:key:abc123")

    def test_wrong_multicodec_prefix(self):
        """A valid base58 string but with wrong multicodec prefix."""
        # Encode bytes that don't start with ED25519 prefix
        wrong_bytes = bytes([0x00, 0x01]) + bytes(range(32))
        encoded = _base58btc_encode(wrong_bytes)
        did = f"did:key:z{encoded}"
        with pytest.raises(ValueError, match="Unexpected multicodec prefix"):
            resolve_did_key(did)

    def test_wrong_key_length(self):
        """Correct multicodec prefix but wrong key length."""
        wrong_bytes = ED25519_MULTICODEC_PREFIX + bytes(range(16))  # 16 instead of 32
        encoded = _base58btc_encode(wrong_bytes)
        did = f"did:key:z{encoded}"
        with pytest.raises(ValueError, match="Expected 32-byte"):
            resolve_did_key(did)


# ---------------------------------------------------------------------------
# did:key creation and resolution round-trip
# ---------------------------------------------------------------------------


class TestCreateDidKey:
    def test_create_and_resolve_roundtrip(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        did = create_did_key(public_key)
        assert did.startswith("did:key:z")

        doc = resolve_did_key(did)
        assert doc.id == did
        vm = doc.key_for_purpose("assertionMethod")
        assert vm is not None
        assert vm.public_key_bytes == public_key.public_bytes_raw()
        assert vm.format == "multibase"
        assert vm.type == "Ed25519VerificationKey2020"

    def test_create_did_key_deterministic(self):
        """Same key → same DID."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        did1 = create_did_key(private_key.public_key())
        did2 = create_did_key(private_key.public_key())
        assert did1 == did2


# ---------------------------------------------------------------------------
# _parse_did_web
# ---------------------------------------------------------------------------


class TestParseDidWeb:
    def test_simple_domain(self):
        url = _parse_did_web("did:web:example.com")
        assert url == "https://example.com/.well-known/did.json"

    def test_domain_with_path(self):
        url = _parse_did_web("did:web:example.com:user:alice")
        assert url == "https://example.com/user/alice/did.json"

    def test_url_encoded_domain(self):
        url = _parse_did_web("did:web:example%2Ecom")
        assert "example.com" in url

    def test_not_did_web(self):
        with pytest.raises(ValueError, match="Not a did:web"):
            _parse_did_web("did:key:z6MkqRY")

    def test_did_web_path_components(self):
        """did:web with multiple path segments should resolve to correct URL."""
        url = _parse_did_web("did:web:example.com:path:to:entity")
        assert url == "https://example.com/path/to/entity/did.json"


# ---------------------------------------------------------------------------
# _decode_jwk
# ---------------------------------------------------------------------------


class TestDecodeJwk:
    def test_decode_ed25519_jwk(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        pub_bytes = private_key.public_key().public_bytes_raw()
        jwk_x = base64.urlsafe_b64encode(pub_bytes).decode("ascii").rstrip("=")
        jwk = {"kty": "OKP", "crv": "Ed25519", "x": jwk_x}
        decoded = _decode_jwk(jwk)
        assert decoded == pub_bytes

    def test_decode_secp256k1_jwk(self):
        # 32-byte x and y coordinates
        x_bytes = bytes(range(32))
        y_bytes = bytes(range(32, 64))
        x_b64 = base64.urlsafe_b64encode(x_bytes).decode("ascii").rstrip("=")
        y_b64 = base64.urlsafe_b64encode(y_bytes).decode("ascii").rstrip("=")
        jwk = {"kty": "EC", "crv": "secp256k1", "x": x_b64, "y": y_b64}
        decoded = _decode_jwk(jwk)
        assert decoded[0] == 0x04  # uncompressed SEC1 prefix
        assert decoded[1:33] == x_bytes
        assert decoded[33:65] == y_bytes

    def test_decode_unsupported_jwk(self):
        with pytest.raises(ValueError, match="Unsupported JWK"):
            _decode_jwk({"kty": "RSA", "crv": "RSA-2048"})

    def test_decode_missing_kty(self):
        with pytest.raises(ValueError, match="Unsupported JWK"):
            _decode_jwk({"crv": "Ed25519"})


# ---------------------------------------------------------------------------
# _vm_from_did_doc_entry
# ---------------------------------------------------------------------------


class TestVmFromDidDocEntry:
    def test_public_key_multibase_ed25519(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        pub_bytes = private_key.public_key().public_bytes_raw()
        raw = ED25519_MULTICODEC_PREFIX + pub_bytes
        encoded = "z" + _base58btc_encode(raw)

        entry = {
            "id": "did:web:example.com#key-1",
            "type": "Ed25519VerificationKey2020",
            "publicKeyMultibase": encoded,
        }
        vm = _vm_from_did_doc_entry(entry, "did:web:example.com")
        assert vm is not None
        assert vm.public_key_bytes == pub_bytes
        assert vm.format == "multibase"

    def test_public_key_multibase_secp256k1(self):
        raw = bytes([0xE7, 0x01]) + bytes(range(64))
        encoded = "z" + _base58btc_encode(raw)

        entry = {
            "id": "did:web:example.com#key-2",
            "type": "EcdsaSecp256k1VerificationKey2019",
            "publicKeyMultibase": encoded,
        }
        vm = _vm_from_did_doc_entry(entry, "did:web:example.com")
        assert vm is not None
        assert vm.format == "multibase"
        assert len(vm.public_key_bytes) == 64

    def test_public_key_base58(self):
        key_bytes = bytes(range(32))
        encoded = _base58btc_encode(key_bytes)
        entry = {
            "id": "did:web:example.com#key-3",
            "type": "Ed25519VerificationKey2018",
            "publicKeyBase58": encoded,
        }
        vm = _vm_from_did_doc_entry(entry, "did:web:example.com")
        assert vm is not None
        assert vm.public_key_bytes == key_bytes
        assert vm.format == "base58"

    def test_public_key_hex(self):
        key_bytes = bytes(range(32))
        entry = {
            "id": "did:web:example.com#key-4",
            "type": "JsonWebKey2020",
            "publicKeyHex": key_bytes.hex(),
        }
        vm = _vm_from_did_doc_entry(entry, "did:web:example.com")
        assert vm is not None
        assert vm.public_key_bytes == key_bytes
        assert vm.format == "hex"

    def test_public_key_jwk(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        pub_bytes = private_key.public_key().public_bytes_raw()
        jwk_x = base64.urlsafe_b64encode(pub_bytes).decode("ascii").rstrip("=")
        entry = {
            "id": "did:web:example.com#key-5",
            "type": "Ed25519VerificationKey2020",
            "publicKeyJwk": {"kty": "OKP", "crv": "Ed25519", "x": jwk_x},
        }
        vm = _vm_from_did_doc_entry(entry, "did:web:example.com")
        assert vm is not None
        assert vm.public_key_bytes == pub_bytes
        assert vm.format == "jwk"

    def test_no_recognized_key_format(self):
        entry = {
            "id": "did:web:example.com#key-6",
            "type": "SomeUnknownType",
            "publicKeyPem": "-----BEGIN PUBLIC KEY-----\n...",
        }
        vm = _vm_from_did_doc_entry(entry, "did:web:example.com")
        assert vm is None

    def test_empty_entry(self):
        vm = _vm_from_did_doc_entry({}, "did:web:example.com")
        assert vm is None


# ---------------------------------------------------------------------------
# resolve_did_web — error paths
# ---------------------------------------------------------------------------


class TestResolveDidWebErrors:
    def test_network_failure_raises_runtime_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            with pytest.raises(RuntimeError, match="Failed to fetch"):
                resolve_did_web("did:web:example.com")

    def test_id_mismatch_raises_value_error(self):
        doc_json = {
            "id": "did:web:wrong.com",
            "verificationMethod": [
                {
                    "id": "did:web:wrong.com#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "publicKeyHex": "00" * 32,
                }
            ],
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            with pytest.raises(ValueError, match="id does not match"):
                resolve_did_web("did:web:example.com")

    def test_no_supported_verification_methods(self):
        doc_json = {
            "id": "did:web:example.com",
            "verificationMethod": [
                {
                    "id": "did:web:example.com#key-1",
                    "type": "UnknownKeyType",
                    "publicKeyPem": "-----BEGIN-----",
                }
            ],
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            with pytest.raises(ValueError, match="no supported verification methods"):
                resolve_did_web("did:web:example.com")

    def test_resolve_with_multibase_key(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        pub_bytes = private_key.public_key().public_bytes_raw()
        raw = ED25519_MULTICODEC_PREFIX + pub_bytes
        encoded = "z" + _base58btc_encode(raw)

        doc_json = {
            "id": "did:web:example.com",
            "verificationMethod": [
                {
                    "id": "did:web:example.com#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "controller": "did:web:example.com",
                    "publicKeyMultibase": encoded,
                }
            ],
            "assertionMethod": ["did:web:example.com#key-1"],
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            doc = resolve_did_web("did:web:example.com")

        assert doc.id == "did:web:example.com"
        vm = doc.key_for_purpose("assertionMethod")
        assert vm is not None
        assert vm.public_key_bytes == pub_bytes

    def test_assertion_method_as_dict(self):
        """assertionMethod can be a single dict instead of a list."""
        key_hex = "00" * 32
        doc_json = {
            "id": "did:web:example.com",
            "verificationMethod": [
                {
                    "id": "did:web:example.com#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "publicKeyHex": key_hex,
                }
            ],
            "assertionMethod": {"id": "did:web:example.com#key-1"},
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            doc = resolve_did_web("did:web:example.com")

        assert doc.assertion_method == ["did:web:example.com#key-1"]

    def test_resolve_with_path(self):
        """did:web with path segments resolves to correct URL."""
        key_hex = "00" * 32
        doc_json = {
            "id": "did:web:example.com:user:alice",
            "verificationMethod": [
                {
                    "id": "did:web:example.com:user:alice#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "publicKeyHex": key_hex,
                }
            ],
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            doc = resolve_did_web("did:web:example.com:user:alice")

        assert doc.id == "did:web:example.com:user:alice"


# ---------------------------------------------------------------------------
# resolve_did_ethr
# ---------------------------------------------------------------------------


class TestResolveDidEthr:
    def test_address_only_did(self):
        """did:ethr:<address> without chain-id."""
        # Mock _require_eth to avoid needing web3.py
        with patch("adl_lite.did_resolver._require_eth", return_value=(None, None)):
            did = "did:ethr:0x1234567890123456789012345678901234567890"
            doc = resolve_did_ethr(did)
        assert doc.id == did
        assert len(doc.verification_methods) == 1
        vm = doc.verification_methods[0]
        assert vm.format == "address"
        assert vm.address == "0x1234567890123456789012345678901234567890"
        assert vm.type == "EcdsaSecp256k1RecoveryMethod2020"

    def test_did_with_chain_id(self):
        """did:ethr:<chain-id>:<address>."""
        with patch("adl_lite.did_resolver._require_eth", return_value=(None, None)):
            did = "did:ethr:1:0x1234567890123456789012345678901234567890"
            doc = resolve_did_ethr(did)
        assert doc.id == did

    def test_invalid_address(self):
        with patch("adl_lite.did_resolver._require_eth", return_value=(None, None)):
            with pytest.raises(ValueError, match="Invalid Ethereum address"):
                resolve_did_ethr("did:ethr:0xinvalid")

    def test_not_did_ethr(self):
        with patch("adl_lite.did_resolver._require_eth", return_value=(None, None)):
            with pytest.raises(ValueError, match="Not a did:ethr"):
                resolve_did_ethr("did:key:z6MkqRY")

    def test_with_rpc_url_owner_match(self):
        """With rpc_url, registry lookup is attempted (best-effort)."""
        mock_web3 = type("MockWeb3", (), {})()
        mock_web3.Web3 = type("MockW3", (), {})()
        mock_web3.Web3.HTTPProvider = lambda url: None
        mock_web3.Web3.to_checksum_address = lambda addr: addr

        mock_contract = type("MockContract", (), {})()
        mock_func = type("MockFunc", (), {})()
        mock_func.call = lambda: "0x1234567890123456789012345678901234567890"
        mock_contract.functions = type("MockFunctions", (), {})()
        mock_contract.functions.identityOwner = lambda addr: mock_func

        mock_w3_instance = type("MockW3Instance", (), {})()
        mock_w3_instance.eth = type("MockEth", (), {})()
        mock_w3_instance.eth.contract = lambda **kw: mock_contract

        mock_web3.Web3 = lambda provider: mock_w3_instance
        mock_web3.Web3.HTTPProvider = lambda url: None
        mock_web3.Web3.to_checksum_address = lambda addr: addr

        with patch("adl_lite.did_resolver._require_eth", return_value=(mock_web3, None)):
            import warnings

            did = "did:ethr:0x1234567890123456789012345678901234567890"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                doc = resolve_did_ethr(did, rpc_url="http://localhost:8545")
            assert doc.id == did

    def test_with_rpc_url_owner_mismatch(self):
        """Registry returns different owner → warning issued but doc still returned."""
        mock_web3 = type("MockWeb3", (), {})()

        mock_contract = type("MockContract", (), {})()
        mock_func = type("MockFunc", (), {})()
        mock_func.call = lambda: "0xdifferentaddress000000000000000000000000000"
        mock_contract.functions = type("MockFunctions", (), {})()
        mock_contract.functions.identityOwner = lambda addr: mock_func

        mock_w3_instance = type("MockW3Instance", (), {})()
        mock_w3_instance.eth = type("MockEth", (), {})()
        mock_w3_instance.eth.contract = lambda **kw: mock_contract

        mock_web3.Web3 = lambda provider: mock_w3_instance
        mock_web3.Web3.HTTPProvider = lambda url: None
        mock_web3.Web3.to_checksum_address = lambda addr: addr

        with patch("adl_lite.did_resolver._require_eth", return_value=(mock_web3, None)):
            import warnings

            did = "did:ethr:0x1234567890123456789012345678901234567890"
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                doc = resolve_did_ethr(did, rpc_url="http://localhost:8545")
                assert len(w) >= 1
                assert "mismatch" in str(w[0].message).lower()
            assert doc.id == did

    def test_with_rpc_url_registry_error(self):
        """Registry lookup failure → warning, doc still returned."""
        mock_web3 = type("MockWeb3", (), {})()

        mock_w3_instance = type("MockW3Instance", (), {})()
        mock_w3_instance.eth = type("MockEth", (), {})()
        mock_w3_instance.eth.contract = lambda **kw: (_ for _ in ()).throw(Exception("RPC error"))

        mock_web3.Web3 = lambda provider: mock_w3_instance
        mock_web3.Web3.HTTPProvider = lambda url: None
        mock_web3.Web3.to_checksum_address = lambda addr: addr

        with patch("adl_lite.did_resolver._require_eth", return_value=(mock_web3, None)):
            import warnings

            did = "did:ethr:0x1234567890123456789012345678901234567890"
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                doc = resolve_did_ethr(did, rpc_url="http://localhost:8545")
                assert len(w) >= 1
            assert doc.id == did


# ---------------------------------------------------------------------------
# DIDResolver multiplexer
# ---------------------------------------------------------------------------


class TestDIDResolver:
    def test_resolve_did_key(self):
        resolver = DIDResolver()
        private_key = ed25519.Ed25519PrivateKey.generate()
        did = create_did_key(private_key.public_key())
        doc = resolver.resolve(did)
        assert doc.id == did

    def test_register_custom_resolver(self):
        resolver = DIDResolver()

        def custom_resolver(did: str, **kwargs):
            return DIDDocument(id=did)

        resolver.register("custom", custom_resolver)
        doc = resolver.resolve("did:custom:test")
        assert doc.id == "did:custom:test"

    def test_unsupported_method(self):
        resolver = DIDResolver()
        with pytest.raises(ValueError, match="Unsupported DID method"):
            resolver.resolve("did:unsupported:test")

    def test_malformed_did_no_method(self):
        with pytest.raises(ValueError, match="Malformed DID"):
            DIDResolver._method("did:only")

    def test_not_a_did(self):
        with pytest.raises(ValueError, match="Not a DID"):
            DIDResolver._method("not-a-did-at-all")

    def test_resolve_did_convenience(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        did = create_did_key(private_key.public_key())
        doc = resolve_did(did)
        assert doc.id == did


# ---------------------------------------------------------------------------
# is_did
# ---------------------------------------------------------------------------


class TestIsDid:
    def test_valid_did_key(self):
        assert is_did("did:key:z6MkqRY") is True

    def test_valid_did_web(self):
        assert is_did("did:web:example.com") is True

    def test_valid_did_ethr(self):
        assert is_did("did:ethr:0x1234567890123456789012345678901234567890") is True

    def test_not_a_string(self):
        assert is_did(123) is False
        assert is_did(None) is False

    def test_does_not_start_with_did(self):
        assert is_did("agent_1") is False
        assert is_did("https://example.com") is False

    def test_unsupported_method(self):
        assert is_did("did:method:not_supported") is False

    def test_too_few_parts(self):
        assert is_did("did:only") is False


# ---------------------------------------------------------------------------
# verify_did_signature
# ---------------------------------------------------------------------------


class TestVerifyDidSignature:
    def test_verify_did_key_valid(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        did = create_did_key(private_key.public_key())
        message = b"test message"
        signature = private_key.sign(message)
        assert verify_did_signature(did, message, signature) is True

    def test_verify_did_key_invalid(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        did = create_did_key(private_key.public_key())
        message = b"test message"
        bad_signature = b"\x00" * 64
        assert verify_did_signature(did, message, bad_signature) is False

    def test_verify_did_web_ed25519_valid(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        pub_bytes = private_key.public_key().public_bytes_raw()
        jwk_x = base64.urlsafe_b64encode(pub_bytes).decode("ascii").rstrip("=")

        doc_json = {
            "id": "did:web:example.com",
            "verificationMethod": [
                {
                    "id": "did:web:example.com#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "controller": "did:web:example.com",
                    "publicKeyJwk": {"kty": "OKP", "crv": "Ed25519", "x": jwk_x},
                }
            ],
            "assertionMethod": ["did:web:example.com#key-1"],
        }
        message = b"web test"
        signature = private_key.sign(message)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            assert verify_did_signature("did:web:example.com", message, signature) is True

    def test_verify_did_web_invalid_signature(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        pub_bytes = private_key.public_key().public_bytes_raw()
        jwk_x = base64.urlsafe_b64encode(pub_bytes).decode("ascii").rstrip("=")

        doc_json = {
            "id": "did:web:example.com",
            "verificationMethod": [
                {
                    "id": "did:web:example.com#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "publicKeyJwk": {"kty": "OKP", "crv": "Ed25519", "x": jwk_x},
                }
            ],
            "assertionMethod": ["did:web:example.com#key-1"],
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            assert verify_did_signature("did:web:example.com", b"msg", b"\x00" * 64) is False

    def test_verify_did_web_no_assertion_method(self):
        """did:web with no usable assertion method returns False."""
        doc_json = {
            "id": "did:web:example.com",
            "verificationMethod": [
                {
                    "id": "did:web:example.com#key-1",
                    "type": "UnknownKeyType",
                    "publicKeyPem": "-----BEGIN-----",
                }
            ],
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            # resolve_did_web will raise ValueError for no supported VMs
            assert verify_did_signature("did:web:example.com", b"msg", b"sig") is False

    def test_verify_unsupported_method_returns_false(self):
        """Unsupported DID method → exception caught → False."""
        result = verify_did_signature("did:unsupported:test", b"msg", b"sig")
        assert result is False


# ---------------------------------------------------------------------------
# _ed25519_public_key_from_doc
# ---------------------------------------------------------------------------


class TestEd25519PublicKeyFromDoc:
    def test_valid_ed25519_doc(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        did = create_did_key(private_key.public_key())
        doc = resolve_did_key(did)
        pk = _ed25519_public_key_from_doc(doc)
        assert pk.public_bytes_raw() == private_key.public_key().public_bytes_raw()

    def test_no_usable_assertion_method(self):
        doc = DIDDocument(id="did:test:test")
        with pytest.raises(ValueError, match="no usable Ed25519"):
            _ed25519_public_key_from_doc(doc)

    def test_wrong_key_type(self):
        vm = VerificationMethod(
            id="did:test:test#key",
            type="WrongKeyType",
            controller="did:test:test",
            public_key_bytes=b"\x00" * 32,
            format="hex",
        )
        doc = DIDDocument(
            id="did:test:test",
            verification_methods=[vm],
            assertion_method=["did:test:test#key"],
        )
        with pytest.raises(ValueError, match="no usable Ed25519"):
            _ed25519_public_key_from_doc(doc)


# ---------------------------------------------------------------------------
# DIDDocument.key_for_purpose
# ---------------------------------------------------------------------------


class TestDIDDocumentKeyForPurpose:
    def test_key_for_assertion_method(self):
        vm = VerificationMethod(
            id="did:test#key-1",
            type="Ed25519VerificationKey2020",
            controller="did:test",
            public_key_bytes=b"\x00" * 32,
            format="multibase",
        )
        doc = DIDDocument(
            id="did:test",
            verification_methods=[vm],
            assertion_method=["did:test#key-1"],
        )
        result = doc.key_for_purpose("assertionMethod")
        assert result is not None
        assert result.id == "did:test#key-1"

    def test_key_for_other_purpose(self):
        """Non-assertionMethod purpose falls back to all VMs."""
        vm = VerificationMethod(
            id="did:test#key-1",
            type="Ed25519VerificationKey2020",
            controller="did:test",
            public_key_bytes=b"\x00" * 32,
            format="multibase",
        )
        doc = DIDDocument(id="did:test", verification_methods=[vm])
        result = doc.key_for_purpose("authentication")
        assert result is not None

    def test_key_for_purpose_empty_assertion(self):
        """Empty assertion_method list falls back to all VMs."""
        vm = VerificationMethod(
            id="did:test#key-1",
            type="Ed25519VerificationKey2020",
            controller="did:test",
            public_key_bytes=b"\x00" * 32,
            format="multibase",
        )
        doc = DIDDocument(id="did:test", verification_methods=[vm], assertion_method=[])
        result = doc.key_for_purpose("assertionMethod")
        assert result is not None

    def test_key_for_purpose_no_vms(self):
        doc = DIDDocument(id="did:test")
        result = doc.key_for_purpose("assertionMethod")
        assert result is None

    def test_key_for_purpose_assertion_id_not_in_vms(self):
        """Assertion method ID doesn't match any VM → returns None."""
        vm = VerificationMethod(
            id="did:test#key-1",
            type="Ed25519VerificationKey2020",
            controller="did:test",
            public_key_bytes=b"\x00" * 32,
            format="multibase",
        )
        doc = DIDDocument(
            id="did:test",
            verification_methods=[vm],
            assertion_method=["did:test#nonexistent"],
        )
        result = doc.key_for_purpose("assertionMethod")
        assert result is None


# ---------------------------------------------------------------------------
# _verify_secp256k1_signature / _verify_ethr_signature
# ---------------------------------------------------------------------------


class TestVerifySecp256k1Signature:
    def test_import_error_when_no_deps(self):
        """When coincurve and ecdsa are both unavailable, raises ImportError."""
        from adl_lite.did_resolver import _verify_secp256k1_signature

        # Mock both imports to fail
        with patch.dict("sys.modules", {"coincurve": None, "ecdsa": None}):
            with pytest.raises(ImportError, match="secp256k1 signature verification"):
                _verify_secp256k1_signature(b"\x00" * 64, b"msg", b"\x00" * 64)


class TestVerifyEthrSignature:
    def test_wrong_signature_length(self):
        """Signatures that aren't 65 bytes should return False."""
        from adl_lite.did_resolver import _verify_ethr_signature

        # eth_account is not installed, so ImportError is raised.
        # But _verify_ethr_signature only checks length AFTER the import,
        # so the ImportError propagates first.
        with pytest.raises(ImportError, match="eth-account"):
            _verify_ethr_signature(
                "did:ethr:0x1234567890123456789012345678901234567890",
                b"message",
                b"\x00" * 64,  # 64 bytes, not 65
            )

    def test_invalid_address(self):
        """When eth_account is not available, ImportError is raised."""
        from adl_lite.did_resolver import _verify_ethr_signature

        with pytest.raises(ImportError, match="eth-account"):
            _verify_ethr_signature(
                "did:ethr:not_a_valid_address",
                b"message",
                b"\x00" * 65,
            )

    def test_verify_did_signature_ethr_no_deps(self):
        """verify_did_signature catches ImportError for did:ethr → returns False."""
        result = verify_did_signature(
            "did:ethr:0x1234567890123456789012345678901234567890",
            b"message",
            b"\x00" * 65,
        )
        assert result is False
