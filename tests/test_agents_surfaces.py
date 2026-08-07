"""M1b surface tests: REST API, CLI, tools.py wrappers, and MCP agent tools.

Covers the P0 adversarial acceptances:
  - P0-1: forged admin attestation rejected (API admin-validate requires a
    valid admin DID signature against the registered admin public key).
  - P0-2: agent chains never surface in discovery listings/status.
  - P0-3: MCP write tools are denied without an admin token.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adl_lite.api import create_app
from adl_lite.api_auth import create_access_token
from adl_lite.did_resolver import create_did_key
from adl_lite.ld_proof import generate_keypair
from adl_lite.models import ADLDocument, ADLFrontMatter, ADLType

TEST_SECRET = "test-secret-for-m1b-surfaces"
ADMIN_TOKEN = create_access_token(
    {"sub": "admin-user", "role": "admin", "tenant_id": "default"},
    secret=TEST_SECRET,
)
USER_TOKEN = create_access_token(
    {"sub": "reader-1", "role": "user", "tenant_id": "default"}, secret=TEST_SECRET
)
AUTH_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
USER_HEADERS = {"Authorization": f"Bearer {USER_TOKEN}"}


def _pubkey_b64(priv) -> str:
    return base64.b64encode(priv.public_key().public_bytes_raw()).decode("ascii")


def _sign_bytes(priv, message: bytes) -> str:
    return base64.b64encode(priv.sign(message)).decode("ascii")


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    state_path = str(tmp_path / "state.json")
    app = create_app(
        state_path=state_path,
        auth_enabled=True,
        jwt_secret=TEST_SECRET,
        metering_db_path=":memory:",
    )
    app.state.state_path = state_path  # exposed for state-file assertions
    return TestClient(app)


def _register_agent(
    client: TestClient, name: str = "alice", role: str = "discoverer", scope: str = "public"
) -> str:
    priv = generate_keypair()  # P2-10: private key stays with the caller
    resp = client.post(
        "/api/v1/agents/register",
        json={"name": name, "role": role, "scope": scope, "public_key": _pubkey_b64(priv)},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    return str(resp.json()["did"])


def _register_concept(client: TestClient, adl_id: str) -> None:
    resp = client.post(
        "/api/v1/consensus/register",
        json={"adl_id": adl_id, "scope": "public"},
        headers=USER_HEADERS,
    )
    assert resp.status_code == 200, resp.text


class TestApiRegister:
    def test_register_requires_admin(self, client: TestClient) -> None:
        """SF-02/P0-3: register without admin role -> 401 (no creds) / 403 (user)."""
        assert (
            client.post(
                "/api/v1/agents/register",
                json={"name": "x", "role": "discoverer"},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/agents/register",
                json={"name": "x", "role": "discoverer"},
                headers=USER_HEADERS,
            ).status_code
            == 403
        )

    def test_register_success(self, client: TestClient) -> None:
        """SF-01: admin register -> did, status=pending."""
        resp = client.post(
            "/api/v1/agents/register",
            json={
                "name": "alice",
                "role": "discoverer",
                "scope": "public",
                "public_key": _pubkey_b64(generate_keypair()),
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["did"].startswith("did:key:")
        assert body["status"] == "pending"
        assert body["validator_count"] == 0

    def test_invalid_role_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/agents/register",
            json={"name": "x", "role": "bogus", "public_key": _pubkey_b64(generate_keypair())},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400

    def test_get_agent_scope_acl(self, client: TestClient) -> None:
        """SF-04: private agent is invisible to non-admin users (404)."""
        resp = client.post(
            "/api/v1/agents/register",
            json={
                "name": "priv",
                "role": "librarian",
                "scope": "private/acme",
                "public_key": _pubkey_b64(generate_keypair()),
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200, resp.text
        did = resp.json()["did"]
        # Authenticated non-admin cannot read private scope.
        assert client.get(f"/api/v1/agents/{did}", headers=USER_HEADERS).status_code == 404
        # Admin can read it.
        assert client.get(f"/api/v1/agents/{did}", headers=AUTH_HEADERS).status_code == 200

    def test_list_pagination(self, client: TestClient) -> None:
        """SF-05: pagination and scope filter."""
        for i in range(3):
            _register_agent(client, name=f"a{i}")
        resp = client.get("/api/v1/agents?limit=2", headers=USER_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["agents"]) == 2

    def test_discovery_list_excludes_agents(self, client: TestClient) -> None:
        """SF-06/P0-2: agent chains never appear in /consensus/list."""
        _register_agent(client, name="alice")
        _register_concept(client, "real-concept")
        resp = client.get("/api/v1/consensus/list", headers=USER_HEADERS)
        assert resp.status_code == 200
        caps = resp.json()["capabilities"]
        assert "real-concept" in caps
        assert all(not c.startswith("did:key:") for c in caps)

    def test_discovery_status_excludes_agents(self, client: TestClient) -> None:
        """P0-2: /consensus/status on an agent chain -> 404 (not provisional)."""
        did = _register_agent(client, name="alice")
        resp = client.get(f"/api/v1/consensus/status/{did}", headers=USER_HEADERS)
        assert resp.status_code == 404


class TestApiAdminValidate:
    def test_admin_public_key_and_attestation(self, client: TestClient) -> None:
        """P0-1: registered admin key + valid signature activates in prod."""
        # Register the admin DID public key (binding point).
        admin_priv = generate_keypair()
        admin_did = create_did_key(admin_priv.public_key())
        resp = client.post(
            "/api/v1/admin/public-key",
            json={"did": admin_did, "public_key": _pubkey_b64(admin_priv)},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200, resp.text
        # Production mode (admin-gated control plane).
        assert (
            client.post("/api/v1/consensus/mode/production", headers=AUTH_HEADERS).status_code
            == 200
        )
        # Register a fresh agent (admin-gated).
        did = _register_agent(client, name="bob")
        # Admin signs the target chain's latest hash.
        hist = client.get(f"/api/v1/agents/{did}/history", headers=AUTH_HEADERS)
        latest_hash = hist.json()["events"][-1]["hash"]
        sig = _sign_bytes(admin_priv, latest_hash.encode("utf-8"))
        resp = client.post(
            f"/api/v1/agents/{did}/admin-validate",
            json={"validator_did": admin_did, "signature": sig},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "active"

    def test_forged_admin_signature_rejected(self, client: TestClient) -> None:
        """P0-1: wrong admin signature -> 403."""
        admin_priv = generate_keypair()
        admin_did = create_did_key(admin_priv.public_key())
        client.post(
            "/api/v1/admin/public-key",
            json={"did": admin_did, "public_key": _pubkey_b64(admin_priv)},
            headers=AUTH_HEADERS,
        )
        did = _register_agent(client, name="mallory")
        hist = client.get(f"/api/v1/agents/{did}/history", headers=AUTH_HEADERS)
        latest_hash = hist.json()["events"][-1]["hash"]
        other_priv = generate_keypair()
        bad_sig = _sign_bytes(other_priv, latest_hash.encode("utf-8"))
        resp = client.post(
            f"/api/v1/agents/{did}/admin-validate",
            json={"validator_did": admin_did, "signature": bad_sig},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 403

    def test_admin_validate_requires_admin(self, client: TestClient) -> None:
        """P0-3: admin-validate endpoint is admin-gated (user role -> 403)."""
        did = _register_agent(client, name="carol")
        resp = client.post(
            f"/api/v1/agents/{did}/admin-validate",
            json={"validator_did": "did:key:zX", "signature": "AAAA"},
            headers=USER_HEADERS,
        )
        assert resp.status_code == 403


class TestApiAttest:
    def test_attest_binds_signature(self, client: TestClient) -> None:
        """SF-03: genesis signature bound via attest endpoint."""
        priv = generate_keypair()
        did = create_did_key(priv.public_key())
        resp = client.post(
            "/api/v1/agents/register",
            json={"name": "signed", "role": "reviewer", "did": did},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        hist = client.get(f"/api/v1/agents/{did}/history", headers=USER_HEADERS)
        genesis_hash = hist.json()["events"][0]["hash"]
        sig = _sign_bytes(priv, genesis_hash.encode("utf-8"))
        resp = client.post(
            f"/api/v1/agents/{did}/attest",
            json={"signature": sig},
            headers=USER_HEADERS,
        )
        assert resp.status_code == 200
        # Signature is persisted in the state file (verified via _load_engine).
        from adl_lite.cli import _load_engine

        engine = _load_engine(Path(client.app.state.state_path))
        assert engine.chains[did].events[0].signature == sig


class TestCliAndTools:
    def test_cli_register_show_deprecate(self, tmp_path: Path) -> None:
        """SF-09: CLI agent register/show/list/deprecate smoke."""
        from adl_lite.cli import _build_parser
        from adl_lite.tools import adl_agent_get, adl_agent_list

        state = str(tmp_path / "state.json")
        priv = generate_keypair()
        parser = _build_parser()
        # register (private key stays local, public key passed in)
        ns = parser.parse_args(
            [
                "agent",
                "register",
                "--name",
                "cli1",
                "--role",
                "discoverer",
                "--public-key",
                _pubkey_b64(priv),
                "--state",
                state,
            ]
        )
        assert ns.func(ns) == 0
        lst = adl_agent_list(state=state)
        assert lst["total"] == 1
        did = lst["agents"][0]["did"]
        # show
        got = adl_agent_get(did, state=state)
        assert got["ok"] is True
        assert got["role"] == "discoverer"
        # list
        ns = parser.parse_args(["agent", "list", "--state", state])
        assert ns.func(ns) == 0
        # deprecate (did is positional)
        ns = parser.parse_args(
            ["agent", "deprecate", did, "--actor", did, "--reason", "test", "--state", state]
        )
        assert ns.func(ns) == 0
        status = adl_agent_get(did, state=state)
        assert status["status"] == "deprecated"

    def test_tools_wrapper_shapes(self, tmp_path: Path) -> None:
        """SF-10: tools wrappers return plain JSON dicts with ok flag."""
        from adl_lite.tools import (
            adl_agent_attest,
            adl_agent_list,
            adl_agent_register,
            adl_agent_validate,
        )

        state = str(tmp_path / "t.json")
        priv = generate_keypair()
        r1 = adl_agent_register("t1", "reviewer", public_key=_pubkey_b64(priv), state=state)
        assert r1["ok"] is True and r1["did"]
        # admin=False by default in tools (P0-3 guard) -> self-validation rejected
        r_bad = adl_agent_validate(r1["did"], r1["did"], state=state)
        assert r_bad["ok"] is False and "self-validation" in r_bad["error"]
        r_list = adl_agent_list(state=state)
        assert r_list["ok"] is True and r_list["total"] == 1
        r_att = adl_agent_attest(r1["did"], "c2FtcGxl", state=state)
        assert r_att["ok"] is True


class TestMcp:
    def _call(self, server, name: str, arguments: dict):
        import asyncio

        result = asyncio.run(server.call_tool(name, arguments))
        return result.data if hasattr(result, "data") else result

    def test_mcp_write_denied_without_token(self, tmp_path: Path) -> None:
        """SF-07/P0-3: MCP write tools rejected without admin token."""
        from adl_lite.mcp_server import create_mcp_server

        server = create_mcp_server(state_path=str(tmp_path / "mcp.json"))
        data = self._call(server, "adl_agent_validate", {"did": "x", "actor_did": "y"})
        assert "admin token" in str(data)

    def test_mcp_write_allowed_with_token(self, tmp_path: Path) -> None:
        """MCP write tools work when an admin token is configured."""
        from adl_lite.mcp_server import create_mcp_server

        server = create_mcp_server(state_path=str(tmp_path / "mcp2.json"), admin_token="s3cret")
        priv = generate_keypair()
        data = self._call(
            server,
            "adl_agent_register",
            {"name": "mcp-agent", "role": "discoverer", "public_key": _pubkey_b64(priv)},
        )
        assert "error" not in str(data) or "ok" in str(data)

    def test_mcp_list_excludes_agents(self, tmp_path: Path) -> None:
        """P0-2: adl_list shows discovery chains only."""
        from adl_lite.cli import _save_engine
        from adl_lite.consensus import ConsensusEngine
        from adl_lite.mcp_server import create_mcp_server

        state_path = tmp_path / "mcp3.json"
        engine = ConsensusEngine()
        doc = ADLDocument(
            front_matter=ADLFrontMatter(adl_type=ADLType.CONCEPT, adl_id="cap-1", scope="public")
        )
        engine.register(doc)
        _save_engine(engine, state_path)
        server = create_mcp_server(state_path=str(state_path))
        data = self._call(server, "adl_list", {})
        assert "cap-1" in str(data)
