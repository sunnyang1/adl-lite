"""Multi-tenant integration tests for the ADL Lite REST API.

Covers:
  * Tenant resolution from JWT ``tenant_id`` claim and API-key mapping.
  * Auth-enabled requests without a tenant claim deriving tenant from identity.
  * Physical isolation: tenant A cannot read/write tenant B's data.
  * Usage endpoint authorization (same tenant / admin; 403 otherwise).
  * Metering increments: ``registered_entities`` on register, ``api_calls`` per call.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import httpx
import pytest
from fastapi.testclient import TestClient

from adl_lite.api import create_app
from adl_lite.api_auth import create_access_token

TEST_SECRET = "test-jwt-secret-multitenant"
TEST_API_KEYS = {"key-acme", "key-beta"}


@pytest.fixture
def auth_app() -> Iterator[TestClient]:
    """Auth-enabled app with two mapped API keys and a fresh meter db."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_path = f.name
    with tempfile.TemporaryDirectory() as td:
        meter_db = str(Path(td) / "meter.db")
        app = create_app(
            state_path=state_path,
            auth_enabled=True,
            jwt_secret=TEST_SECRET,
            api_keys=TEST_API_KEYS,
            api_key_tenants={"key-acme": "acme", "key-beta": "beta"},
            metering_db_path=meter_db,
        )
        yield TestClient(app)
    Path(state_path).unlink(missing_ok=True)


def _jwt(sub: str, role: str = "user", tenant_id: str | None = None) -> str:
    data: dict = {"sub": sub, "role": role}
    if tenant_id is not None:
        data["tenant_id"] = tenant_id
    return create_access_token(data, secret=TEST_SECRET)


def _usage(
    client: TestClient, tenant_id: str, as_tenant: str | None = None, as_role: str = "user"
) -> httpx.Response:
    headers = {"Authorization": f"Bearer {_jwt(as_tenant or tenant_id, role=as_role)}"}
    return cast(httpx.Response, client.get(f"/api/v1/tenants/{tenant_id}/usage", headers=headers))


def _jwt_reg(client: TestClient, tenant_id: str, adl_id: str) -> None:
    client.post(
        "/api/v1/consensus/register",
        json={"adl_id": adl_id, "domain": "test", "scope": "public"},
        headers={"Authorization": f"Bearer {_jwt(tenant_id, tenant_id=tenant_id)}"},
    )


# --- tenant resolution -----------------------------------------------------


def test_jwt_tenant_claim_used(auth_app: TestClient) -> None:
    token = _jwt("user-acme", tenant_id="acme")
    resp = auth_app.post(
        "/api/v1/consensus/register",
        json={"adl_id": "acme-cap", "domain": "test", "scope": "public"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    usage = _usage(auth_app, "acme", as_tenant="acme")
    assert usage.status_code == 200
    assert usage.json()["registered_entities"] == 1


def test_apikey_tenant_mapping(auth_app: TestClient) -> None:
    resp = auth_app.post(
        "/api/v1/consensus/register",
        json={"adl_id": "beta-cap", "domain": "test", "scope": "public"},
        headers={"X-API-Key": "key-beta"},
    )
    assert resp.status_code == 200
    usage = _usage(auth_app, "beta", as_tenant="beta")
    assert usage.json()["registered_entities"] == 1


def test_auth_enabled_no_claim_derives_from_identity(auth_app: TestClient) -> None:
    # JWT without a tenant_id claim → tenant derived from `sub`.
    token = _jwt("derived-user")
    resp = auth_app.post(
        "/api/v1/consensus/register",
        json={"adl_id": "derived-cap", "domain": "test", "scope": "public"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    usage = _usage(auth_app, "derived-user", as_tenant="derived-user")
    assert usage.status_code == 200


# --- physical isolation ----------------------------------------------------


def test_cross_tenant_physical_isolation(auth_app: TestClient) -> None:
    auth_app.post(
        "/api/v1/consensus/register",
        json={"adl_id": "shared-id", "domain": "test", "scope": "public"},
        headers={"Authorization": f"Bearer {_jwt('acme', tenant_id='acme')}"},
    )
    # Tenant beta queries the same adl_id → should be 404 (separate state).
    resp = auth_app.get(
        "/api/v1/consensus/status/shared-id",
        headers={"Authorization": f"Bearer {_jwt('beta', tenant_id='beta')}"},
    )
    assert resp.status_code == 404


# --- usage authorization ---------------------------------------------------


def test_usage_same_tenant_ok(auth_app: TestClient) -> None:
    _jwt_reg(auth_app, "acme", "acme-cap")
    assert _usage(auth_app, "acme", as_tenant="acme").status_code == 200


def test_usage_other_tenant_forbidden(auth_app: TestClient) -> None:
    _jwt_reg(auth_app, "acme", "acme-cap")
    resp = _usage(auth_app, "acme", as_tenant="beta", as_role="user")
    assert resp.status_code == 403


def test_usage_admin_ok(auth_app: TestClient) -> None:
    _jwt_reg(auth_app, "acme", "acme-cap")
    resp = _usage(auth_app, "acme", as_tenant="admin", as_role="admin")
    assert resp.status_code == 200


# --- metering increments ---------------------------------------------------


def test_register_increments_entity_and_calls(auth_app: TestClient) -> None:
    before = _usage(auth_app, "acme", as_tenant="acme").json()["api_calls"]
    _jwt_reg(auth_app, "acme", "acme-cap-x")
    after = _usage(auth_app, "acme", as_tenant="acme").json()
    assert after["registered_entities"] == 1
    assert after["api_calls"] == before + 2  # +1 register, +1 usage query itself


def test_api_call_increment_only(auth_app: TestClient) -> None:
    _jwt_reg(auth_app, "acme", "acme-cap-y")
    before = _usage(auth_app, "acme", as_tenant="acme").json()["api_calls"]
    auth_app.get(
        "/api/v1/consensus/status/acme-cap-y",
        headers={"Authorization": f"Bearer {_jwt('acme', tenant_id='acme')}"},
    )
    after = _usage(auth_app, "acme", as_tenant="acme").json()["api_calls"]
    assert after == before + 2  # +1 status query, +1 usage query itself


def test_export_csv_and_json(auth_app: TestClient) -> None:
    _jwt_reg(auth_app, "acme", "acme-cap-z")
    csv_r = auth_app.get(
        "/api/v1/tenants/acme/usage/export?format=csv",
        headers={"Authorization": f"Bearer {_jwt('acme', tenant_id='acme')}"},
    )
    assert csv_r.status_code == 200
    assert "tenant_id" in csv_r.text

    json_r = auth_app.get(
        "/api/v1/tenants/acme/usage/export?format=json",
        headers={"Authorization": f"Bearer {_jwt('acme', tenant_id='acme')}"},
    )
    assert json_r.status_code == 200
    assert json_r.json()[0]["tenant_id"] == "acme"


def test_export_invalid_format(auth_app: TestClient) -> None:
    _jwt_reg(auth_app, "acme", "acme-cap-bad")
    resp = auth_app.get(
        "/api/v1/tenants/acme/usage/export?format=xml",
        headers={"Authorization": f"Bearer {_jwt('acme', tenant_id='acme')}"},
    )
    assert resp.status_code == 400
