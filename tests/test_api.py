"""Tests for adl_lite.api — FastAPI REST API for consensus lifecycle."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adl_lite.api import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient with a fresh engine backed by a temp state file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_path = f.name
    app = create_app(state_path=state_path)
    tc = TestClient(app)
    yield tc
    # Cleanup temp file
    Path(state_path).unlink(missing_ok=True)


# ── Smoke tests: app creation & schema ──────────────────────────────────


class TestAppCreation:
    """Verify the FastAPI app can be created and its schema is correct."""

    def test_app_title_via_openapi(self, client: TestClient):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        assert resp.json()["info"]["title"] == "ADL Lite Consensus API"

    def test_app_version_via_openapi(self, client: TestClient):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        assert resp.json()["info"]["version"] == "0.5.0-alpha"

    def test_docs_endpoint_returns_200(self, client: TestClient):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_has_nine_paths(self, client: TestClient):
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        expected = [
            "/api/v1/consensus/register",
            "/api/v1/consensus/transition",
            "/api/v1/consensus/status/{adl_id}",
            "/api/v1/consensus/history/{adl_id}",
            "/api/v1/consensus/fork",
            "/api/v1/consensus/verify/{adl_id}",
            "/api/v1/consensus/list",
            "/api/v1/consensus/mode/dev",
            "/api/v1/consensus/mode/production",
        ]
        assert len(paths) == len(expected)
        for p in expected:
            assert p in paths


# ── Endpoint functional tests ───────────────────────────────────────────


class TestRegisterEndpoint:
    """Test POST /api/v1/consensus/register."""

    def test_register_success(self, client: TestClient):
        payload = {
            "adl_id": "test_api_register",
            "domain": "test",
            "scope": "public",
        }
        resp = client.post("/api/v1/consensus/register", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["adl_id"] == "test_api_register"
        assert body["status"] == "provisional"

    def test_register_duplicate_returns_409(self, client: TestClient):
        payload = {
            "adl_id": "test_api_dup",
            "domain": "test",
            "scope": "public",
        }
        resp1 = client.post("/api/v1/consensus/register", json=payload)
        assert resp1.status_code == 200
        resp2 = client.post("/api/v1/consensus/register", json=payload)
        assert resp2.status_code == 409

    def test_register_missing_adl_id_returns_422(self, client: TestClient):
        payload = {"domain": "test", "scope": "public"}
        # Missing required field adl_id -> FastAPI 422
        resp = client.post("/api/v1/consensus/register", json=payload)
        assert resp.status_code == 422


class TestTransitionEndpoint:
    """Test POST /api/v1/consensus/transition."""

    def test_transition_discovered_to_validated(self, client: TestClient):
        # Register first
        reg_payload = {"adl_id": "test_api_trans", "domain": "test", "scope": "public"}
        client.post("/api/v1/consensus/register", json=reg_payload)
        # Then transition (dev mode → N_min=1, so single validator works)
        trans_payload = {
            "adl_id": "test_api_trans",
            "to_status": "validated",
            "actor": "validator-1",
            "reason": "api test transition",
        }
        resp = client.post("/api/v1/consensus/transition", json=trans_payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["adl_id"] == "test_api_trans"
        assert body["status"] == "validated"

    def test_transition_invalid_status_returns_400(self, client: TestClient):
        reg_payload = {"adl_id": "test_api_trans_inv", "domain": "test", "scope": "public"}
        client.post("/api/v1/consensus/register", json=reg_payload)
        trans_payload = {
            "adl_id": "test_api_trans_inv",
            "to_status": "nonsense_status",
            "actor": "validator-1",
        }
        resp = client.post("/api/v1/consensus/transition", json=trans_payload)
        assert resp.status_code == 400


class TestStatusEndpoint:
    """Test GET /api/v1/consensus/status/{adl_id}."""

    def test_status_of_registered_concept(self, client: TestClient):
        payload = {"adl_id": "test_api_status", "domain": "test", "scope": "public"}
        client.post("/api/v1/consensus/register", json=payload)
        resp = client.get("/api/v1/consensus/status/test_api_status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["adl_id"] == "test_api_status"
        assert body["status"] == "provisional"

    def test_status_of_unregistered_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/consensus/status/nonexistent")
        assert resp.status_code == 404


class TestListEndpoint:
    """Test GET /api/v1/consensus/list."""

    def test_list_returns_registered_concepts(self, client: TestClient):
        payload = {"adl_id": "test_api_list", "domain": "test", "scope": "public"}
        client.post("/api/v1/consensus/register", json=payload)
        resp = client.get("/api/v1/consensus/list")
        assert resp.status_code == 200
        body = resp.json()
        assert "capabilities" in body
        assert "count" in body
        assert "test_api_list" in body["capabilities"]


class TestModeEndpoints:
    """Test /api/v1/consensus/mode/dev and /mode/production."""

    def test_set_dev_mode(self, client: TestClient):
        resp = client.post("/api/v1/consensus/mode/dev")
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "dev"
        assert body["n_min"] == 1
        assert body["dev_mode"] is True

    def test_set_production_mode(self, client: TestClient):
        resp = client.post("/api/v1/consensus/mode/production")
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "production"
        assert body["dev_mode"] is False


class TestVerifyEndpoint:
    """Test GET /api/v1/consensus/verify/{adl_id}."""

    def test_verify_registered_concept(self, client: TestClient):
        payload = {"adl_id": "test_api_verify", "domain": "test", "scope": "public"}
        client.post("/api/v1/consensus/register", json=payload)
        resp = client.get("/api/v1/consensus/verify/test_api_verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body["adl_id"] == "test_api_verify"
        assert "integrity_ok" in body

    def test_verify_unregistered_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/consensus/verify/nonexistent")
        assert resp.status_code == 404


class TestHistoryEndpoint:
    """Test GET /api/v1/consensus/history/{adl_id}."""

    def test_history_of_registered_concept(self, client: TestClient):
        payload = {"adl_id": "test_api_hist", "domain": "test", "scope": "public"}
        client.post("/api/v1/consensus/register", json=payload)
        resp = client.get("/api/v1/consensus/history/test_api_hist")
        assert resp.status_code == 200
        body = resp.json()
        assert body["adl_id"] == "test_api_hist"
        assert isinstance(body["events"], list)
        # Should have at least the genesis event
        assert len(body["events"]) >= 1

    def test_history_of_unregistered_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/consensus/history/nonexistent")
        assert resp.status_code == 404


class TestForkEndpoint:
    """Test POST /api/v1/consensus/fork."""

    def test_fork_registered_concept(self, client: TestClient):
        # Register and validate first (forking requires validated status)
        reg_payload = {"adl_id": "test_api_fork", "domain": "test", "scope": "public"}
        client.post("/api/v1/consensus/register", json=reg_payload)
        trans_payload = {
            "adl_id": "test_api_fork",
            "to_status": "validated",
            "actor": "validator-1",
            "reason": "api test",
        }
        client.post("/api/v1/consensus/transition", json=trans_payload)
        # Now fork
        fork_payload = {
            "original_id": "test_api_fork",
            "fork_id": "test_api_fork_child",
            "actor": "forker-1",
            "reason": "api fork test",
        }
        resp = client.post("/api/v1/consensus/fork", json=fork_payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["adl_id"] == "test_api_fork_child"
