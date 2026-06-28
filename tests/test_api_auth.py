"""TDD tests for API hardening — JWT auth, API key auth, pagination, rate limiting.

Behaviors B1-1 through B4-3 (16 total). Written FIRST in TDD red phase.
"""

from __future__ import annotations

import tempfile
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jose import JWTError

from adl_lite.api import create_app
from adl_lite.api_auth import (
    RateLimiter,
    create_access_token,
    get_current_user,
    verify_api_key,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET = "test-jwt-secret-for-adl-lite"
TEST_API_KEYS = {"test-key-1", "test-key-2"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_auth_client(
    auth_enabled: bool = True,
    rate_limit: int = 0,
) -> TestClient:
    """Create a TestClient with auth-enabled app and a temp state file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_path = f.name
    app = create_app(
        state_path=state_path,
        auth_enabled=auth_enabled,
        jwt_secret=TEST_SECRET,
        api_keys=TEST_API_KEYS,
        rate_limit=rate_limit,
    )
    tc = TestClient(app)
    yield tc
    Path(state_path).unlink(missing_ok=True)


@pytest.fixture
def auth_client() -> TestClient:
    """Auth-enabled client with rate limiting disabled."""
    gen = _make_auth_client(auth_enabled=True, rate_limit=0)
    yield from gen


@pytest.fixture
def no_auth_client() -> TestClient:
    """Auth-disabled client (backward compat)."""
    gen = _make_auth_client(auth_enabled=False, rate_limit=0)
    yield from gen


@pytest.fixture
def rate_limited_client() -> TestClient:
    """Auth-enabled client with low rate limit for testing."""
    gen = _make_auth_client(auth_enabled=True, rate_limit=5)
    yield from gen


def _register_payload(adl_id: str = "test_b1") -> dict:
    return {"adl_id": adl_id, "domain": "test", "scope": "public"}


def _make_jwt(
    sub: str = "user1",
    role: str = "user",
    secret: str = TEST_SECRET,
    expires: timedelta | None = None,
) -> str:
    return create_access_token({"sub": sub, "role": role}, secret=secret, expires_delta=expires)


# ===========================================================================
# B1: JWT Authentication Middleware (6 behaviors)
# ===========================================================================


class TestJWTAuth:
    """B1-1 through B1-6: JWT authentication behaviors."""

    # B1-1: No auth header → 401
    def test_no_auth_header_returns_401(self, auth_client: TestClient):
        """POST /register without Authorization or X-API-Key → 401."""
        resp = auth_client.post("/api/v1/consensus/register", json=_register_payload())
        assert resp.status_code == 401
        assert "Not authenticated" in resp.json()["detail"]

    # B1-2: Valid JWT → 200
    def test_valid_jwt_returns_200(self, auth_client: TestClient):
        """POST /register with valid JWT → 200."""
        token = _make_jwt(sub="user1", role="user")
        resp = auth_client.post(
            "/api/v1/consensus/register",
            json=_register_payload("jwt_valid_test"),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["adl_id"] == "jwt_valid_test"

    # B1-3: Expired JWT → 401
    def test_expired_jwt_returns_401(self, auth_client: TestClient):
        """POST /register with expired JWT → 401, 'Token expired'."""
        token = _make_jwt(sub="user1", role="user", expires=timedelta(seconds=-1))
        resp = auth_client.post(
            "/api/v1/consensus/register",
            json=_register_payload("jwt_expired_test"),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert "Token expired" in resp.json()["detail"]

    # B1-4: Invalid JWT signature → 401
    def test_invalid_jwt_signature_returns_401(self, auth_client: TestClient):
        """POST /register with JWT signed with wrong secret → 401."""
        token = _make_jwt(sub="user1", role="user", secret="WRONG-SECRET")
        resp = auth_client.post(
            "/api/v1/consensus/register",
            json=_register_payload("jwt_bad_sig_test"),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["detail"]

    # B1-5: Non-admin JWT on mode endpoint → 403
    def test_non_admin_jwt_on_mode_returns_403(self, auth_client: TestClient):
        """POST /mode/dev with role=user JWT → 403, 'Admin access required'."""
        token = _make_jwt(sub="regular-user", role="user")
        resp = auth_client.post(
            "/api/v1/consensus/mode/dev",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert "Admin access required" in resp.json()["detail"]

    # B1-6: Admin JWT on mode endpoint → 200
    def test_admin_jwt_on_mode_returns_200(self, auth_client: TestClient):
        """POST /mode/dev with role=admin JWT → 200."""
        token = _make_jwt(sub="admin-user", role="admin")
        resp = auth_client.post(
            "/api/v1/consensus/mode/dev",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["mode"] == "dev"


# ===========================================================================
# B2: API Key Authentication (3 behaviors)
# ===========================================================================


class TestAPIKeyAuth:
    """B2-1 through B2-3: API key authentication behaviors."""

    # B2-1: Valid API key → 200
    def test_valid_api_key_returns_200(self, auth_client: TestClient):
        """POST /register with valid X-API-Key → 200."""
        resp = auth_client.post(
            "/api/v1/consensus/register",
            json=_register_payload("apikey_valid_test"),
            headers={"X-API-Key": "test-key-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["adl_id"] == "apikey_valid_test"

    # B2-2: Invalid API key → 401
    def test_invalid_api_key_returns_401(self, auth_client: TestClient):
        """POST /register with wrong X-API-Key → 401, 'Invalid API key'."""
        resp = auth_client.post(
            "/api/v1/consensus/register",
            json=_register_payload("apikey_invalid_test"),
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401
        assert "Invalid API key" in resp.json()["detail"]

    # B2-3: JWT and API key both work (dual auth)
    def test_dual_auth_both_paths_work(self, auth_client: TestClient):
        """Both JWT and API key independently authenticate successfully."""
        # JWT path
        token = _make_jwt(sub="dual-user", role="user")
        resp_jwt = auth_client.post(
            "/api/v1/consensus/register",
            json=_register_payload("dual_jwt_test"),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_jwt.status_code == 200

        # API key path
        resp_key = auth_client.post(
            "/api/v1/consensus/register",
            json=_register_payload("dual_apikey_test"),
            headers={"X-API-Key": "test-key-2"},
        )
        assert resp_key.status_code == 200


# ===========================================================================
# B3: Pagination for /list endpoint (4 behaviors)
# ===========================================================================


class TestPagination:
    """B3-1 through B3-4: Pagination behaviors for /list endpoint."""

    def _register_many(self, client: TestClient, n: int, prefix: str = "pag") -> None:
        """Register n concepts using auth headers."""
        token = _make_jwt(sub="pag-user", role="user")
        for i in range(n):
            resp = client.post(
                "/api/v1/consensus/register",
                json={"adl_id": f"{prefix}-{i}", "domain": "test", "scope": "public"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    # B3-1: Default pagination returns total + offset/limit
    def test_default_pagination(self, auth_client: TestClient):
        """GET /list returns total, offset=0, limit=50, capabilities list."""
        self._register_many(auth_client, 3, prefix="def_pag")
        token = _make_jwt(sub="pag-user", role="user")
        resp = auth_client.get(
            "/api/v1/consensus/list",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "offset" in body
        assert "limit" in body
        assert "capabilities" in body
        assert body["offset"] == 0
        assert body["limit"] == 50

    # B3-2: Custom offset/limit
    def test_custom_offset_limit(self, auth_client: TestClient):
        """GET /list?offset=0&limit=5 returns first 5, total still shows full count."""
        self._register_many(auth_client, 8, prefix="cust_pag")
        token = _make_jwt(sub="pag-user", role="user")
        resp = auth_client.get(
            "/api/v1/consensus/list?offset=0&limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["capabilities"]) == 5
        assert body["total"] >= 8  # total includes all registered capabilities
        assert body["offset"] == 0
        assert body["limit"] == 5

    # B3-3: Offset beyond data range
    def test_offset_beyond_data_range(self, auth_client: TestClient):
        """GET /list?offset=10&limit=5 when only 5 caps → capabilities=[], total=5."""
        self._register_many(auth_client, 5, prefix="off_pag")
        token = _make_jwt(sub="pag-user", role="user")
        resp = auth_client.get(
            "/api/v1/consensus/list?offset=10&limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["capabilities"] == []
        assert body["total"] == 5
        assert body["offset"] == 10

    # B3-4: Limit exceeds max → 400
    def test_limit_exceeds_max_returns_400(self, auth_client: TestClient):
        """GET /list?limit=201 → 400, 'Limit cannot exceed 200'."""
        token = _make_jwt(sub="pag-user", role="user")
        resp = auth_client.get(
            "/api/v1/consensus/list?limit=201",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "Limit cannot exceed 200" in resp.json()["detail"]


# ===========================================================================
# B4: Rate Limiting (3 behaviors)
# ===========================================================================


class TestRateLimiting:
    """B4-1 through B4-3: Rate limiting behaviors."""

    # B4-1: Within rate limit → normal
    def test_within_rate_limit_returns_200(self, rate_limited_client: TestClient):
        """Send 5 requests within rate limit → all return 200."""
        token = _make_jwt(sub="rl-user", role="user")
        for i in range(5):
            resp = rate_limited_client.post(
                "/api/v1/consensus/register",
                json={"adl_id": f"rl_within_{i}", "domain": "test", "scope": "public"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    # B4-2: Over rate limit → 429 with Retry-After
    def test_over_rate_limit_returns_429(self, rate_limited_client: TestClient):
        """6th request with rate_limit=5 → 429 with Retry-After header."""
        token = _make_jwt(sub="rl-over-user", role="user")
        # First 5 should succeed
        for i in range(5):
            resp = rate_limited_client.post(
                "/api/v1/consensus/register",
                json={"adl_id": f"rl_over_ok_{i}", "domain": "test", "scope": "public"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
        # 6th should be rate-limited
        resp = rate_limited_client.post(
            "/api/v1/consensus/register",
            json={"adl_id": "rl_over_blocked", "domain": "test", "scope": "public"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        retry_after = int(resp.headers["Retry-After"])
        assert retry_after > 0

    # B4-3: Rate limit window reset → normal
    def test_rate_limit_window_reset(self, rate_limited_client: TestClient):
        """After window expires, previously rate-limited client can make requests."""
        token = _make_jwt(sub="rl-reset-user", role="user")
        # Use 5 requests to fill the limit
        for i in range(5):
            rate_limited_client.post(
                "/api/v1/consensus/register",
                json={"adl_id": f"rl_reset_{i}", "domain": "test", "scope": "public"},
                headers={"Authorization": f"Bearer {token}"},
            )
        # 6th should be blocked
        resp = rate_limited_client.post(
            "/api/v1/consensus/register",
            json={"adl_id": "rl_reset_blocked", "domain": "test", "scope": "public"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 429

        # Now mock time to advance past the window
        # The RateLimiter uses time.time() — patch it to advance 61 seconds
        current_time = time.time()
        with patch("time.time", return_value=current_time + 61):
            # After window reset, requests should succeed again
            resp = rate_limited_client.post(
                "/api/v1/consensus/register",
                json={"adl_id": "rl_reset_after", "domain": "test", "scope": "public"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200


# ===========================================================================
# Backward compatibility: auth_enabled=False preserves existing behavior
# ===========================================================================


class TestAuthDisabledBackwardCompat:
    """When auth_enabled=False, existing tests should still pass."""

    def test_register_without_auth(self, no_auth_client: TestClient):
        """POST /register without any auth → 200 (auth disabled)."""
        resp = no_auth_client.post(
            "/api/v1/consensus/register",
            json=_register_payload("noauth_reg"),
        )
        assert resp.status_code == 200

    def test_list_without_auth(self, no_auth_client: TestClient):
        """GET /list without auth → 200 (auth disabled)."""
        resp = no_auth_client.get("/api/v1/consensus/list")
        assert resp.status_code == 200

    def test_mode_without_auth(self, no_auth_client: TestClient):
        """POST /mode/dev without auth → 200 (auth disabled)."""
        resp = no_auth_client.post("/api/v1/consensus/mode/dev")
        assert resp.status_code == 200


# ===========================================================================
# Unit tests for api_auth module functions
# ===========================================================================


class TestCreateAccessToken:
    """Unit tests for create_access_token."""

    def test_create_token_returns_string(self):
        """create_access_token returns a non-empty string."""
        token = create_access_token({"sub": "test"}, secret=TEST_SECRET)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_expiry(self):
        """create_access_token with expires_delta produces a valid token."""
        token = create_access_token(
            {"sub": "test"}, secret=TEST_SECRET, expires_delta=timedelta(hours=1)
        )
        payload = get_current_user(token, TEST_SECRET)
        assert payload["sub"] == "test"


class TestGetCurrentUser:
    """Unit tests for get_current_user."""

    def test_decode_valid_token(self):
        """get_current_user decodes a valid token and returns payload."""
        token = create_access_token({"sub": "user1", "role": "admin"}, secret=TEST_SECRET)
        payload = get_current_user(token, TEST_SECRET)
        assert payload["sub"] == "user1"
        assert payload["role"] == "admin"

    def test_decode_wrong_secret_raises(self):
        """get_current_user with wrong secret raises an error."""
        token = create_access_token({"sub": "user1"}, secret=TEST_SECRET)
        with pytest.raises(JWTError):
            get_current_user(token, "WRONG-SECRET")


class TestVerifyApiKey:
    """Unit tests for verify_api_key."""

    def test_valid_key_returns_identity(self):
        """verify_api_key returns key identity for valid key."""
        result = verify_api_key("test-key-1", TEST_API_KEYS)
        assert result is not None
        assert result == "test-key-1"

    def test_invalid_key_returns_none(self):
        """verify_api_key returns None for invalid key."""
        result = verify_api_key("wrong-key", TEST_API_KEYS)
        assert result is None


class TestRateLimiterUnit:
    """Unit tests for RateLimiter."""

    def test_check_within_limit(self):
        """RateLimiter.check returns True when within limit."""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        assert rl.check("client-1") is True

    def test_check_over_limit(self):
        """RateLimiter.check returns False when over limit."""
        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            rl.check("client-1")
        assert rl.check("client-1") is False

    def test_get_retry_after(self):
        """RateLimiter.get_retry_after returns positive seconds."""
        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            rl.check("client-1")
        rl.check("client-1")  # triggers over-limit
        retry = rl.get_retry_after("client-1")
        assert retry > 0
        assert retry <= 60
