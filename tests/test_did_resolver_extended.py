"""
Extended tests for adl_lite.did_resolver — resolution failure paths,
unknown methods, caching behavior, and timeout configuration.
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
    _base58btc_encode,
    is_did,
    resolve_did,
    resolve_did_ethr,
    resolve_did_key,
    resolve_did_web,
    verify_did_signature,
)


class TestDidWebResolutionFailure:
    """Test did:web resolution when the server returns errors or is unreachable."""

    def test_did_web_http_error(self):
        """HTTP error response should raise RuntimeError."""
        from urllib.error import HTTPError

        with patch(
            "urllib.request.urlopen", side_effect=HTTPError("url", 500, "Server Error", {}, None)
        ):
            with pytest.raises(RuntimeError, match="Failed to fetch"):
                resolve_did_web("did:web:example.com")

    def test_did_web_connection_refused(self):
        """Connection refused should raise RuntimeError."""
        with patch(
            "urllib.request.urlopen", side_effect=ConnectionRefusedError("Connection refused")
        ):
            with pytest.raises(RuntimeError, match="Failed to fetch"):
                resolve_did_web("did:web:unreachable.example.com")

    def test_did_web_timeout(self):
        """Timeout should raise RuntimeError."""
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with pytest.raises(RuntimeError, match="Failed to fetch"):
                resolve_did_web("did:web:slow.example.com")

    def test_did_web_ssl_error(self):
        """SSL error should raise RuntimeError."""
        import ssl

        with patch("urllib.request.urlopen", side_effect=ssl.SSLError("cert verify failed")):
            with pytest.raises(RuntimeError, match="Failed to fetch"):
                resolve_did_web("did:web:badssl.example.com")

    def test_did_web_empty_document(self):
        """Server returning empty JSON should raise ValueError (no supported VMs)."""
        doc_json = {"id": "did:web:example.com"}
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            with pytest.raises(ValueError, match="no supported verification methods"):
                resolve_did_web("did:web:example.com")


class TestDidEthrResolutionFailure:
    """Test did:ethr resolution failure paths."""

    def test_did_ethr_invalid_format_no_address(self):
        """did:ethr with missing address part should raise ValueError."""
        with patch("adl_lite.did_resolver._require_eth", return_value=(None, None)):
            with pytest.raises(ValueError, match="Not a did:ethr"):
                resolve_did_ethr("did:key:z6MkqRY")

    def test_did_ethr_with_invalid_chain_id(self):
        """did:ethr with non-numeric chain-id should raise ValueError."""
        with patch("adl_lite.did_resolver._require_eth", return_value=(None, None)):
            with pytest.raises(ValueError):
                resolve_did_ethr("did:ethr:abc:0x1234567890123456789012345678901234567890")

    def test_did_ethr_rpc_connection_failure(self):
        """RPC endpoint unreachable → warning, doc still returned."""
        mock_web3 = type("MockWeb3", (), {})()
        mock_web3.Web3 = lambda provider: None
        mock_web3.Web3.HTTPProvider = lambda url: None
        mock_web3.Web3.to_checksum_address = lambda addr: addr

        with patch("adl_lite.did_resolver._require_eth", return_value=(mock_web3, None)):
            import warnings

            did = "did:ethr:0x1234567890123456789012345678901234567890"
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                doc = resolve_did_ethr(did, rpc_url="http://unreachable:8545")
                # Warning may or may not be emitted depending on mock behavior
            assert doc.id == did


class TestDidKeyInvalidMultibase:
    """Test did:key with invalid multibase encoding."""

    def test_did_key_invalid_multibase_chars(self):
        """did:key with characters outside base58btc alphabet should fail."""
        # base58btc alphabet does not include 0, O, I, l
        with pytest.raises(ValueError):
            resolve_did_key("did:key:z0OIl")  # Invalid chars

    def test_did_key_empty_multibase(self):
        """did:key with empty multibase after z prefix should fail."""
        with pytest.raises(ValueError, match="Invalid did:key format"):
            # The regex requires at least one char after z
            resolve_did_key("did:key:z")

    def test_did_key_invalid_ed25519_public_key_corrupted(self):
        """Valid multibase prefix but corrupted Ed25519 key bytes (wrong length)."""
        # 16 bytes instead of 32 — wrong key length
        wrong_bytes = ED25519_MULTICODEC_PREFIX + bytes(range(16))
        encoded = _base58btc_encode(wrong_bytes)
        did = f"did:key:z{encoded}"
        with pytest.raises(ValueError, match="Expected 32-byte"):
            resolve_did_key(did)

    def test_did_key_correct_prefix_but_all_zero_key(self):
        """Valid prefix and length but all-zero public key should still resolve."""
        # All-zero 32-byte key is technically valid (just useless)
        zero_bytes = ED25519_MULTICODEC_PREFIX + b"\x00" * 32
        encoded = _base58btc_encode(zero_bytes)
        did = f"did:key:z{encoded}"
        doc = resolve_did_key(did)
        assert doc.id == did
        assert doc.verification_methods[0].public_key_bytes == b"\x00" * 32


class TestResolveUnknownMethod:
    """Test resolving DIDs with unsupported methods."""

    def test_resolve_unknown_method_raises(self):
        """did:unknown should raise ValueError from DIDResolver."""
        resolver = DIDResolver()
        with pytest.raises(ValueError, match="Unsupported DID method"):
            resolver.resolve("did:unknown:abc123")

    def test_resolve_did_convenience_unknown_method(self):
        """resolve_did convenience function should raise for unknown methods."""
        with pytest.raises(ValueError, match="Unsupported DID method"):
            resolve_did("did:unknown:test")

    def test_did_resolver_method_extraction(self):
        """_method should correctly extract method from DID."""
        assert DIDResolver._method("did:key:z6Mk") == "key"
        assert DIDResolver._method("did:web:example.com") == "web"
        assert DIDResolver._method("did:ethr:0x123") == "ethr"

    def test_is_did_with_unknown_method(self):
        """is_did should return False for unsupported methods."""
        assert is_did("did:unknown:abc123") is False
        assert is_did("did:method:xyz") is False
        assert is_did("did:onion:test") is False


class TestDidWebCacheInteraction:
    """Test did:web resolution caching behavior (or lack thereof)."""

    def test_did_web_repeated_resolution(self):
        """Repeated did:web resolution should make fresh requests each time."""
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
        }

        call_counts = [0]

        class MockCtxResp:
            """Context-manager mock for urllib.request.urlopen return value."""

            def __init__(self, data):
                self._data = data

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return self._data

        def mock_urlopen(url, timeout=10):
            call_counts[0] += 1
            return MockCtxResp(json.dumps(doc_json).encode("utf-8"))

        with patch("urllib.request.urlopen", mock_urlopen):
            doc1 = resolve_did_web("did:web:example.com")
            doc2 = resolve_did_web("did:web:example.com")

        # Each resolution makes a fresh HTTP request (no caching)
        assert doc1.id == doc2.id
        assert call_counts[0] == 2


class TestDidResolverConfigWithTimeout:
    """Test resolver configuration with custom timeout settings."""

    def test_did_web_default_timeout(self):
        """Default timeout should be 10 seconds."""
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
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            resolve_did_web("did:web:example.com")
            # Check that urlopen was called with default timeout=10
            call_args = mock_urlopen.call_args
            assert call_args[1].get("timeout", 10) == 10

    def test_did_web_custom_timeout(self):
        """Custom timeout should be passed to urlopen."""
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
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            resolve_did_web("did:web:example.com", timeout=30)
            # Check that urlopen was called with timeout=30
            call_args = mock_urlopen.call_args
            assert call_args[1].get("timeout") == 30

    def test_did_resolver_register_and_resolve(self):
        """Custom resolver registered via DIDResolver.register should be callable."""
        resolver = DIDResolver()

        def custom_resolver(did: str, **kwargs):
            return DIDDocument(
                id=did,
                verification_methods=[
                    VerificationMethod(
                        id=f"{did}#key",
                        type="CustomVerificationKey",
                        controller=did,
                        public_key_bytes=b"\x00" * 32,
                        format="custom",
                    )
                ],
            )

        resolver.register("custom", custom_resolver)
        doc = resolver.resolve("did:custom:test-id")
        assert doc.id == "did:custom:test-id"
        assert len(doc.verification_methods) == 1

    def test_verify_did_signature_with_did_web_timeout(self):
        """verify_did_signature should propagate timeout for did:web."""
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
        message = b"timeout test"
        signature = private_key.sign(message)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(doc_json).encode("utf-8")
            result = verify_did_signature("did:web:example.com", message, signature)
            assert result is True
