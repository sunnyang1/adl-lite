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

    def test_openapi_has_expected_paths(self, client: TestClient):
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
            "/api/v1/consensus/mode",
            "/api/v1/consensus/mode/dev",
            "/api/v1/consensus/mode/production",
            "/api/v1/tenants/{tenant_id}/usage",
            "/api/v1/tenants/{tenant_id}/usage/export",
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


# ── Internal function tests ────────────────────────────────────────────


class TestInternalFunctions:
    """Tests for _get_engine lazy loading, transition error handling,
    and fork error handling. Covers lines 121-144, 222-225, 228, 279-282."""

    def test_get_engine_lazy_load_from_disk(self, tmp_path: Path):
        """Create a temporary JSON state file with a registered concept,
        call _get_engine() with that state_path. Verify the engine loads
        correctly, the concept chain is present, and subsequent API calls
        use the loaded engine. Covers lines 121-144."""
        import json

        from adl_lite.api import _get_engine

        # Create a state file with a registered concept
        state_file = tmp_path / "lazy_load_state.json"
        state_data = {
            "chains": {
                "lazy-concept": [
                    {
                        "event_type": "register",
                        "actor": "test-actor",
                        "reasoning": "lazy load test",
                        "timestamp": "2024-01-01T00:00:00+00:00",
                        "payload": {},
                    }
                ]
            }
        }
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        # Reset module-level globals so the engine is lazily loaded fresh
        import adl_lite.api

        adl_lite.api._state_path = state_file
        adl_lite.api._engine = None

        # Call _get_engine — should load state from disk
        engine = _get_engine()
        assert engine is not None
        assert "lazy-concept" in engine.chains

        # Verify the loaded chain has events
        chain = engine.chains["lazy-concept"]
        assert len(chain.events) >= 1
        assert chain.events[0].event_type.value == "register"

        # Clean up globals
        adl_lite.api._engine = None
        adl_lite.api._state_path = Path("adl_consensus.json")

    def test_transition_event_none_error(self, client: TestClient):
        """POST to /api/v1/consensus/transition with a body that would
        cause engine.transition() to return None.
        Verify the endpoint returns a 500 error. Covers lines 222-225, 228."""
        from unittest.mock import patch

        # Register a concept first
        reg_payload = {"adl_id": "trans_none_test2", "domain": "test", "scope": "public"}
        client.post("/api/v1/consensus/register", json=reg_payload)

        # Patch the engine's transition method to return None
        # We patch on the actual engine instance, not the factory function
        import adl_lite.api

        engine = adl_lite.api._get_engine()

        def mock_transition_return_none(*args, **kwargs):
            return None

        with patch.object(engine, "transition", side_effect=mock_transition_return_none):
            trans_payload = {
                "adl_id": "trans_none_test2",
                "to_status": "validated",
                "actor": "validator-1",
                "reason": "test none event",
            }
            resp = client.post("/api/v1/consensus/transition", json=trans_payload)
            assert resp.status_code == 500
            assert (
                "Transition failed" in resp.json()["detail"]
                or "no event returned" in resp.json()["detail"].lower()
            )

        # Reset engine singleton so next test gets fresh state
        adl_lite.api._engine = None

    def test_fork_keyerror_handling(self, client: TestClient):
        """POST to /api/v1/consensus/fork with an original_id that doesn't
        exist in engine.chains, causing KeyError. Verify KeyError is caught
        and 404 is returned. Covers lines 279-282."""
        fork_payload = {
            "original_id": "nonexistent_for_fork",
            "fork_id": "fork_child_keyerror",
            "actor": "forker-1",
            "reason": "testing KeyError handling",
        }
        resp = client.post("/api/v1/consensus/fork", json=fork_payload)
        # KeyError should be caught and return 404
        assert resp.status_code == 404

    def test_fork_consensus_error_handling(self, client: TestClient):
        """POST to /api/v1/consensus/fork with parameters that would cause
        ADLConsensusError (e.g., trying to fork an archived concept,
        since archived → forked is not a valid transition).
        Verify ADLConsensusError is caught and 409 is returned.
        Covers lines 279-282."""

        # Register a concept
        reg_payload = {"adl_id": "fork_cons_archived", "domain": "test", "scope": "public"}
        client.post("/api/v1/consensus/register", json=reg_payload)

        # Transition it to archived status (via validated then deprecated)
        client.post(
            "/api/v1/consensus/transition",
            json={
                "adl_id": "fork_cons_archived",
                "to_status": "validated",
                "actor": "v1",
                "reason": "validate",
            },
        )
        client.post(
            "/api/v1/consensus/transition",
            json={
                "adl_id": "fork_cons_archived",
                "to_status": "deprecated",
                "actor": "v2",
                "reason": "deprecate",
            },
        )
        client.post(
            "/api/v1/consensus/transition",
            json={
                "adl_id": "fork_cons_archived",
                "to_status": "archived",
                "actor": "v3",
                "reason": "archive",
            },
        )

        # Attempt to fork an archived concept — should cause ADLConsensusError
        # because archived → forked is not a valid transition
        fork_payload = {
            "original_id": "fork_cons_archived",
            "fork_id": "fork_cons_archived_child",
            "actor": "forker-1",
            "reason": "testing consensus error on archived",
        }
        resp = client.post("/api/v1/consensus/fork", json=fork_payload)
        # ADLConsensusError should be caught and return 409
        assert resp.status_code == 409
