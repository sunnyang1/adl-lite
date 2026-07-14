"""Tests for adl_lite.quota — QuotaPolicy, QuotaConfig, check_quota (R12).

Covers:
  * Default no-limit path → 200
  * Global quota api_calls exceeded → 429
  * Global quota entities exceeded → 429
  * Tenant-specific quota isolation
  * 429 response body format
  * Control-plane endpoints exempt from quota
  * Usage endpoints themselves consume api_calls
  * Quota reset on period boundary crossing
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adl_lite.api import _quota_config, create_app
from adl_lite.api_auth import create_access_token
from adl_lite.quota import (
    QuotaConfig,
    QuotaPolicy,
    configure_quota,
    get_quota_config,
)

TEST_SECRET = "test-jwt-secret-quota"
TEST_API_KEYS = {"key-acme", "key-widgetco"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def quota_app() -> Iterator[TestClient]:
    """Auth-enabled app with two tenants mapped via API keys, no quota by default."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_path = f.name
    with tempfile.TemporaryDirectory() as td:
        meter_db = str(Path(td) / "meter.db")
        app = create_app(
            state_path=state_path,
            auth_enabled=True,
            jwt_secret=TEST_SECRET,
            api_keys=TEST_API_KEYS,
            api_key_tenants={"key-acme": "acme", "key-widgetco": "widgetco"},
            metering_db_path=meter_db,
        )
        yield TestClient(app)
    Path(state_path).unlink(missing_ok=True)


def _jwt(sub: str, role: str = "user", tenant_id: str | None = None) -> str:
    data: dict = {"sub": sub, "role": role}
    if tenant_id is not None:
        data["tenant_id"] = tenant_id
    return create_access_token(data, secret=TEST_SECRET)


def _api_key_headers(key: str) -> dict:
    return {"X-API-Key": key}


def _auth_headers(identity: str, role: str = "user", tid: str | None = None) -> dict:
    return {"Authorization": f"Bearer {_jwt(identity, role=role, tenant_id=tid)}"}


# ---------------------------------------------------------------------------
# QuotaPolicy unit tests
# ---------------------------------------------------------------------------


class TestQuotaPolicy:
    """Verify QuotaPolicy model defaults and serialization."""

    def test_default_policy_is_unlimited(self) -> None:
        p = QuotaPolicy()
        assert p.max_api_calls is None
        assert p.max_entities is None
        assert p.period == "monthly"

    def test_parse_from_dict(self) -> None:
        p = QuotaPolicy.model_validate({"max_api_calls": 100, "period": "daily"})
        assert p.max_api_calls == 100
        assert p.max_entities is None
        assert p.period == "daily"

    def test_max_api_calls_zero_means_block_all(self) -> None:
        """max_api_calls=0 is a valid 'deny-all' policy (not None = unlimited)."""
        p = QuotaPolicy(max_api_calls=0)
        assert p.max_api_calls == 0
        assert p.max_entities is None


# ---------------------------------------------------------------------------
# QuotaConfig unit tests
# ---------------------------------------------------------------------------


class TestQuotaConfig:
    """Verify QuotaConfig thread-safe singleton behaviour."""

    def test_default_returns_unlimited(self) -> None:
        qc = QuotaConfig()
        p = qc.get_policy("any-tenant")
        assert p.max_api_calls is None
        assert p.max_entities is None

    def test_global_override(self) -> None:
        qc = QuotaConfig()
        qc.set_global(QuotaPolicy(max_api_calls=5000))
        p = qc.get_policy("any-tenant")
        assert p.max_api_calls == 5000

    def test_tenant_override_takes_priority(self) -> None:
        qc = QuotaConfig()
        qc.set_global(QuotaPolicy(max_api_calls=1000))
        qc.set_tenant("acme", QuotaPolicy(max_api_calls=50000))
        assert qc.get_policy("acme").max_api_calls == 50000
        assert qc.get_policy("widgetco").max_api_calls == 1000

    def test_reset_clears_all(self) -> None:
        qc = QuotaConfig()
        qc.set_global(QuotaPolicy(max_api_calls=1000))
        qc.set_tenant("acme", QuotaPolicy(max_api_calls=5000))
        qc.reset()
        assert qc.get_policy("acme").max_api_calls is None
        assert qc.get_policy("widgetco").max_api_calls is None

    def test_set_tenant_then_unset_via_reset(self) -> None:
        qc = QuotaConfig()
        qc.set_tenant("acme", QuotaPolicy(max_entities=50))
        assert qc.get_policy("acme").max_entities == 50
        qc.reset()
        assert qc.get_policy("acme").max_entities is None


# ---------------------------------------------------------------------------
# Convenience function tests
# ---------------------------------------------------------------------------


class TestConfigureQuota:
    def test_global_via_star(self) -> None:
        get_quota_config().reset()
        configure_quota(max_api_calls=42)
        assert get_quota_config().get_policy("acme").max_api_calls == 42
        get_quota_config().reset()

    def test_tenant_specific(self) -> None:
        get_quota_config().reset()
        configure_quota("acme", max_api_calls=99)
        assert get_quota_config().get_policy("acme").max_api_calls == 99
        assert get_quota_config().get_policy("widgetco").max_api_calls is None
        get_quota_config().reset()


# ---------------------------------------------------------------------------
# Integration tests — default no-limits path
# ---------------------------------------------------------------------------


class TestDefaultNoQuotaLimit:
    """When no quota is configured, everything behaves as before."""

    def test_register_works_without_quota(self, quota_app: TestClient) -> None:
        resp = quota_app.post(
            "/api/v1/consensus/register",
            json={"adl_id": "cap-1", "scope": "public", "domain": "test"},
            headers=_api_key_headers("key-acme"),
        )
        assert resp.status_code == 200

    def test_transition_works_without_quota(self, quota_app: TestClient) -> None:
        quota_app.post(
            "/api/v1/consensus/register",
            json={"adl_id": "cap-t1", "scope": "public", "domain": "test"},
            headers=_api_key_headers("key-acme"),
        )
        resp = quota_app.post(
            "/api/v1/consensus/transition",
            json={
                "adl_id": "cap-t1",
                "to_status": "validated",
                "actor": "tester",
                "reason": "test",
            },
            headers=_api_key_headers("key-acme"),
        )
        assert resp.status_code == 200

    def test_usage_endpoint_works_without_quota(self, quota_app: TestClient) -> None:
        resp = quota_app.get(
            "/api/v1/tenants/acme/usage",
            headers=_api_key_headers("key-acme"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == "acme"

    def test_export_endpoint_works_without_quota(self, quota_app: TestClient) -> None:
        resp = quota_app.get(
            "/api/v1/tenants/acme/usage/export",
            headers=_api_key_headers("key-acme"),
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Integration tests — global quota api_calls exceeded
# ---------------------------------------------------------------------------


class TestGlobalQuotaApiCallsExceeded:
    """Verify 429 is raised when a tenant exceeds the global api_calls limit."""

    @pytest.fixture(autouse=True)
    def _setup(self, quota_app: TestClient) -> None:
        _quota_config.reset()
        configure_quota(max_api_calls=5)

    def test_first_five_requests_succeed(self, quota_app: TestClient) -> None:
        for i in range(5):
            resp = quota_app.get(
                "/api/v1/consensus/list",
                headers=_api_key_headers("key-acme"),
            )
            assert resp.status_code == 200, f"Request {i + 1} expected 200, got {resp.status_code}"

    def test_sixth_request_returns_429(self, quota_app: TestClient) -> None:
        headers = _api_key_headers("key-acme")
        for _ in range(5):
            quota_app.get("/api/v1/consensus/list", headers=headers)
        resp = quota_app.get("/api/v1/consensus/list", headers=headers)
        assert resp.status_code == 429

    def test_register_at_limit_returns_429(self, quota_app: TestClient) -> None:
        """When api_calls already at the limit, any metered endpoint → 429."""
        headers = _api_key_headers("key-acme")
        # Burn through the quota.
        for _ in range(5):
            quota_app.get("/api/v1/consensus/list", headers=headers)
        # Now even register (which hasn't been called yet) should be blocked.
        resp = quota_app.post(
            "/api/v1/consensus/register",
            json={"adl_id": "should-fail", "scope": "public", "domain": "test"},
            headers=headers,
        )
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Integration tests — global quota entities exceeded
# ---------------------------------------------------------------------------


class TestGlobalQuotaEntitiesExceeded:
    """Verify 429 is raised when a tenant exceeds the global entities limit."""

    @pytest.fixture(autouse=True)
    def _setup(self, quota_app: TestClient) -> None:
        _quota_config.reset()
        configure_quota(max_entities=2)

    def test_first_two_registrations_succeed(self, quota_app: TestClient) -> None:
        headers = _api_key_headers("key-acme")
        r1 = quota_app.post(
            "/api/v1/consensus/register",
            json={"adl_id": "ent-1", "scope": "public", "domain": "test"},
            headers=headers,
        )
        assert r1.status_code == 200
        r2 = quota_app.post(
            "/api/v1/consensus/register",
            json={"adl_id": "ent-2", "scope": "public", "domain": "test"},
            headers=headers,
        )
        assert r2.status_code == 200

    def test_third_registration_returns_429(self, quota_app: TestClient) -> None:
        headers = _api_key_headers("key-acme")
        # Register two different concepts (different adl_id avoids 409).
        quota_app.post(
            "/api/v1/consensus/register",
            json={"adl_id": "ent-a", "scope": "public", "domain": "test"},
            headers=headers,
        )
        quota_app.post(
            "/api/v1/consensus/register",
            json={"adl_id": "ent-b", "scope": "public", "domain": "test"},
            headers=headers,
        )
        # Third should be blocked by quota BEFORE handler runs.
        resp = quota_app.post(
            "/api/v1/consensus/register",
            json={"adl_id": "ent-c", "scope": "public", "domain": "test"},
            headers=headers,
        )
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Integration tests — tenant-specific quota isolation
# ---------------------------------------------------------------------------


class TestTenantSpecificQuota:
    """Tenant A is restricted; tenant B remains unlimited."""

    @pytest.fixture(autouse=True)
    def _setup(self, quota_app: TestClient) -> None:
        _quota_config.reset()
        configure_quota("acme", max_api_calls=3)

    def test_acme_exceeds_quota(self, quota_app: TestClient) -> None:
        h = _api_key_headers("key-acme")
        for _ in range(3):
            quota_app.get("/api/v1/consensus/list", headers=h)
        # 4th call → 429
        resp = quota_app.get("/api/v1/consensus/list", headers=h)
        assert resp.status_code == 429

    def test_widgetco_still_unlimited(self, quota_app: TestClient) -> None:
        # Make many calls as widgetco — all should succeed.
        h = _api_key_headers("key-widgetco")
        for i in range(10):
            resp = quota_app.get("/api/v1/consensus/list", headers=h)
            assert resp.status_code == 200, f"widgetco call {i + 1} failed with {resp.status_code}"

    def test_isolation_acme_quota_does_not_affect_widgetco(self, quota_app: TestClient) -> None:
        h_acme = _api_key_headers("key-acme")
        h_widget = _api_key_headers("key-widgetco")
        # Exhaust acme.
        for _ in range(3):
            quota_app.get("/api/v1/consensus/list", headers=h_acme)
        assert quota_app.get("/api/v1/consensus/list", headers=h_acme).status_code == 429
        # widgetco still fine.
        assert quota_app.get("/api/v1/consensus/list", headers=h_widget).status_code == 200


# ---------------------------------------------------------------------------
# Integration tests — 429 response format
# ---------------------------------------------------------------------------


class Test429ResponseFormat:
    @pytest.fixture(autouse=True)
    def _setup(self, quota_app: TestClient) -> None:
        _quota_config.reset()
        configure_quota(max_api_calls=1)

    def test_429_body_contains_required_keys(self, quota_app: TestClient) -> None:
        headers = _api_key_headers("key-acme")
        # Burn the single allowed call.
        quota_app.get("/api/v1/consensus/list", headers=headers)
        # Trigger 429.
        resp = quota_app.get("/api/v1/consensus/list", headers=headers)
        assert resp.status_code == 429
        body = resp.json()
        # FastAPI wraps HTTPException(detail=...) as {"detail": ...}
        detail = body["detail"]
        assert isinstance(detail, dict)
        assert "error" in detail
        assert detail["error"] == "quota_exceeded"
        assert "detail" in detail
        assert "quota" in detail
        assert "max_api_calls" in detail["quota"]
        assert "current" in detail
        assert "api_calls" in detail["current"]
        assert "retry_after" in detail

    def test_429_body_quota_reflects_configured_limits(self, quota_app: TestClient) -> None:
        headers = _api_key_headers("key-acme")
        quota_app.get("/api/v1/consensus/list", headers=headers)
        resp = quota_app.get("/api/v1/consensus/list", headers=headers)
        detail = resp.json()["detail"]
        assert detail["quota"]["max_api_calls"] == 1
        assert detail["quota"]["max_entities"] is None
        assert detail["quota"]["period"] == "monthly"

    def test_429_retry_after_is_iso8601(self, quota_app: TestClient) -> None:
        headers = _api_key_headers("key-acme")
        quota_app.get("/api/v1/consensus/list", headers=headers)
        resp = quota_app.get("/api/v1/consensus/list", headers=headers)
        retry_after = resp.json()["detail"]["retry_after"]
        # Must be ISO-8601 with Z suffix, e.g. "2026-08-01T00:00:00Z".
        assert retry_after.endswith("Z")
        datetime.fromisoformat(retry_after.replace("Z", "+00:00"))

    def test_429_current_reflects_usage_snapshot(self, quota_app: TestClient) -> None:
        headers = _api_key_headers("key-acme")
        quota_app.get("/api/v1/consensus/list", headers=headers)
        resp = quota_app.get("/api/v1/consensus/list", headers=headers)
        current = resp.json()["detail"]["current"]
        assert current["api_calls"] >= 1
        assert "registered_entities" in current
        assert "period_start" in current
        assert "period_end" in current


# ---------------------------------------------------------------------------
# Control-plane exemption
# ---------------------------------------------------------------------------


class TestControlPlaneExempt:
    """Control-plane endpoints (POST /mode/dev, POST /mode/production)
    use ``require_admin`` and must never be blocked by quotas."""

    @pytest.fixture(autouse=True)
    def _setup(self, quota_app: TestClient) -> None:  # noqa: ARG002 — force ordering
        _quota_config.reset()
        configure_quota(max_api_calls=0)  # Block ALL data-plane calls.

    def test_mode_dev_not_blocked(self, quota_app: TestClient) -> None:
        headers = _auth_headers("admin", role="admin")
        resp = quota_app.post("/api/v1/consensus/mode/dev", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["mode"] == "dev"

    def test_mode_production_not_blocked(self, quota_app: TestClient) -> None:
        headers = _auth_headers("admin", role="admin")
        resp = quota_app.post("/api/v1/consensus/mode/production", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["mode"] == "production"

    def test_data_plane_is_blocked_when_quota_is_zero(self, quota_app: TestClient) -> None:
        """With max_api_calls=0 the very first data-plane call is denied."""
        resp = quota_app.get(
            "/api/v1/consensus/list",
            headers=_api_key_headers("key-acme"),
        )
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Usage endpoints themselves consume quota
# ---------------------------------------------------------------------------


class TestUsageEndpointsCounted:
    """The usage query endpoints go through meter_api_call, so they
    consume api_calls quota just like any other data-plane endpoint."""

    @pytest.fixture(autouse=True)
    def _setup(self, quota_app: TestClient) -> None:  # noqa: ARG002 — force ordering
        _quota_config.reset()
        configure_quota(max_api_calls=3)

    def test_usage_query_counts_toward_quota(self, quota_app: TestClient) -> None:
        h = _api_key_headers("key-acme")
        # 3 usage queries → should consume 3 api_calls.
        for _ in range(3):
            resp = quota_app.get("/api/v1/tenants/acme/usage", headers=h)
            assert resp.status_code == 200
        # 4th usage query → 429.
        resp = quota_app.get("/api/v1/tenants/acme/usage", headers=h)
        assert resp.status_code == 429

    def test_export_query_counts_toward_quota(self, quota_app: TestClient) -> None:
        h = _api_key_headers("key-acme")
        # 2 export + 1 list = 3 calls → next is 429.
        quota_app.get("/api/v1/tenants/acme/usage/export", headers=h)
        quota_app.get("/api/v1/tenants/acme/usage/export", headers=h)
        quota_app.get("/api/v1/consensus/list", headers=h)
        resp = quota_app.get("/api/v1/consensus/list", headers=h)
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Quota reset on new period
# ---------------------------------------------------------------------------


class TestQuotaResetOnNewPeriod:
    """When the clock crosses a period boundary the counter effectively resets
    (the new period window has zero usage)."""

    def test_crossing_month_boundary_resets_count(
        self, quota_app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _quota_config.reset()
        configure_quota(max_api_calls=2)

        h = _api_key_headers("key-acme")
        # Burn the quota in the current month.
        quota_app.get("/api/v1/consensus/list", headers=h)
        quota_app.get("/api/v1/consensus/list", headers=h)
        assert quota_app.get("/api/v1/consensus/list", headers=h).status_code == 429

        # Advance time to the next month.
        now = datetime.now(timezone.utc)
        if now.month == 12:
            next_month = now.replace(
                year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        else:
            next_month = now.replace(
                month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
            )

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return next_month

        monkeypatch.setattr("adl_lite.quota.datetime", _FrozenDatetime)
        # Also patch in metering since the meter records with its own now().
        # But the key here is that check_quota uses quota.py's datetime.now()
        # to compute the period window. Since the metering data is in SQLite
        # with period_start from the old month, get_record for the new month
        # returns zero-filled, so quota check passes.

        # After period rollover, new calls should succeed (new window = 0).
        resp = quota_app.get("/api/v1/consensus/list", headers=h)
        assert resp.status_code == 200
