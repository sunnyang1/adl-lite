"""Integration tests for the scope ACL on API/MCP read paths (P0-4).

Covers the document visibility matrix for the ``scope`` taxonomy
(``public`` / ``private/<org>`` / ``user/<id>`` / ``shared/<collab>``):

* auth disabled  → the anonymous reader sees only ``public`` documents.
* auth enabled   → a caller sees ``public`` + ``private/<their tenant>`` +
  ``user/<their identity>``; ``admin`` sees everything.
* ``/list`` filters invisible documents; single-document reads return 404
  (existence is not leaked).
* MCP read tools (no tenant context) expose ``public`` documents only.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adl_lite.api import create_app
from adl_lite.api_auth import create_access_token

TEST_SECRET = "test-jwt-secret-scope-acl"
TEST_API_KEYS = {"key-acme", "key-beta"}


@pytest.fixture
def noauth_app() -> Iterator[TestClient]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_path = f.name
    app = create_app(state_path=state_path, auth_enabled=False)
    yield TestClient(app)
    Path(state_path).unlink(missing_ok=True)


@pytest.fixture
def auth_app() -> Iterator[TestClient]:
    """Auth-enabled app with API-key tenants acme/beta."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_path = f.name
    with tempfile.TemporaryDirectory() as td:
        app = create_app(
            state_path=state_path,
            auth_enabled=True,
            jwt_secret=TEST_SECRET,
            api_keys=TEST_API_KEYS,
            api_key_tenants={"key-acme": "acme", "key-beta": "beta"},
            metering_db_path=str(Path(td) / "meter.db"),
        )
        yield TestClient(app)
    Path(state_path).unlink(missing_ok=True)


def _jwt(sub: str, role: str = "user", tenant_id: str | None = None) -> dict:
    data: dict = {"sub": sub, "role": role}
    if tenant_id is not None:
        data["tenant_id"] = tenant_id
    return {"Authorization": f"Bearer {create_access_token(data, secret=TEST_SECRET)}"}


def _key(key: str) -> dict:
    return {"X-API-Key": key}


def _register(client: TestClient, adl_id: str, scope: str, headers: dict | None = None) -> int:
    resp = client.post(
        "/api/v1/consensus/register",
        json={"adl_id": adl_id, "domain": "test", "scope": scope},
        headers=headers or {},
    )
    return int(resp.status_code)


def _listed(client: TestClient, headers: dict | None = None) -> list[str]:
    resp = client.get("/api/v1/consensus/list", headers=headers or {})
    assert resp.status_code == 200
    return list(resp.json()["capabilities"])


# ---------------------------------------------------------------------------
# Auth disabled — anonymous reader sees public only
# ---------------------------------------------------------------------------


class TestAnonymousReaderVisibility:
    def test_public_doc_visible(self, noauth_app: TestClient) -> None:
        assert _register(noauth_app, "acl-pub", "public") == 200
        resp = noauth_app.get("/api/v1/consensus/status/acl-pub")
        assert resp.status_code == 200
        assert "acl-pub" in _listed(noauth_app)

    @pytest.mark.parametrize("scope", ["private/acme", "user/alice", "shared/team-x"])
    def test_non_public_doc_hidden(self, noauth_app: TestClient, scope: str) -> None:
        assert _register(noauth_app, f"acl-hidden-{scope.replace('/', '-')}", scope) == 200
        adl_id = f"acl-hidden-{scope.replace('/', '-')}"
        # Single-document reads: 404 (existence not leaked).
        assert noauth_app.get(f"/api/v1/consensus/status/{adl_id}").status_code == 404
        assert noauth_app.get(f"/api/v1/consensus/history/{adl_id}").status_code == 404
        assert noauth_app.get(f"/api/v1/consensus/verify/{adl_id}").status_code == 404
        # List: filtered out.
        assert adl_id not in _listed(noauth_app)


# ---------------------------------------------------------------------------
# Auth enabled — tenant / user / admin matrix
# ---------------------------------------------------------------------------


class TestAuthenticatedVisibility:
    def test_private_tenant_doc_visible_to_same_tenant(self, auth_app: TestClient) -> None:
        assert _register(auth_app, "acl-acme-priv", "private/acme", _key("key-acme")) == 200
        # Same tenant (acme) can read it.
        resp = auth_app.get("/api/v1/consensus/status/acl-acme-priv", headers=_key("key-acme"))
        assert resp.status_code == 200
        assert "acl-acme-priv" in _listed(auth_app, _key("key-acme"))

    def test_private_tenant_doc_hidden_from_other_tenant(self, auth_app: TestClient) -> None:
        assert _register(auth_app, "acl-acme-priv2", "private/acme", _key("key-acme")) == 200
        # beta cannot read acme's private doc.
        resp = auth_app.get("/api/v1/consensus/status/acl-acme-priv2", headers=_key("key-beta"))
        assert resp.status_code == 404
        assert "acl-acme-priv2" not in _listed(auth_app, _key("key-beta"))

    def test_user_doc_visible_only_to_that_user(self, auth_app: TestClient) -> None:
        alice = _jwt("alice", tenant_id="acme")
        bob = _jwt("bob", tenant_id="acme")
        assert _register(auth_app, "acl-alice-doc", "user/alice", alice) == 200
        assert (
            auth_app.get("/api/v1/consensus/status/acl-alice-doc", headers=alice).status_code == 200
        )
        assert "acl-alice-doc" in _listed(auth_app, alice)
        # Same tenant, different user → hidden.
        assert (
            auth_app.get("/api/v1/consensus/status/acl-alice-doc", headers=bob).status_code == 404
        )
        assert "acl-alice-doc" not in _listed(auth_app, bob)

    def test_shared_doc_not_guessed_by_tenant(self, auth_app: TestClient) -> None:
        """shared/<collab> requires exact scope match; tenants don't map onto it."""
        assert _register(auth_app, "acl-shared", "shared/team-x", _key("key-acme")) == 200
        assert (
            auth_app.get(
                "/api/v1/consensus/status/acl-shared", headers=_key("key-acme")
            ).status_code
            == 404
        )

    def test_admin_reads_everything(self, auth_app: TestClient) -> None:
        """Admin role bypasses the scope ACL within its tenant engine.

        Note: per-tenant engines are physically isolated (separate state
        files), so the admin authenticates with the target tenant claim —
        mirroring the pre-existing usage-endpoint admin semantics.
        """
        assert _register(auth_app, "acl-admin-priv", "private/acme", _key("key-acme")) == 200
        assert (
            _register(auth_app, "acl-admin-user", "user/alice", _jwt("alice", tenant_id="acme"))
            == 200
        )
        admin = _jwt("root", role="admin", tenant_id="acme")
        for adl_id in ("acl-admin-priv", "acl-admin-user"):
            resp = auth_app.get(f"/api/v1/consensus/status/{adl_id}", headers=admin)
            assert resp.status_code == 200
        listed = _listed(auth_app, admin)
        assert "acl-admin-priv" in listed
        assert "acl-admin-user" in listed

    def test_public_doc_visible_to_all_authenticated(self, auth_app: TestClient) -> None:
        """Public docs are visible to any authenticated caller in the same tenant."""
        assert _register(auth_app, "acl-pub-all", "public", _key("key-acme")) == 200
        for headers in (_key("key-acme"), _jwt("alice", tenant_id="acme")):
            resp = auth_app.get("/api/v1/consensus/status/acl-pub-all", headers=headers)
            assert resp.status_code == 200

    def test_scope_survives_state_reload(self, auth_app: TestClient) -> None:
        """The genesis SNAPSHOT payload persists scope across engine reloads."""
        assert _register(auth_app, "acl-reload", "private/acme", _key("key-acme")) == 200
        import adl_lite.api as api_module

        # Force engine reload from the persisted state file.
        api_module._engine = None
        api_module._engine_cache.clear()
        assert (
            auth_app.get(
                "/api/v1/consensus/status/acl-reload", headers=_key("key-acme")
            ).status_code
            == 200
        )
        assert (
            auth_app.get(
                "/api/v1/consensus/status/acl-reload", headers=_key("key-beta")
            ).status_code
            == 404
        )


# ---------------------------------------------------------------------------
# MCP server — read tools expose public scope only
# ---------------------------------------------------------------------------


class TestMcpScopeAcl:
    @pytest.fixture
    def mcp_server(self, tmp_path: Path):
        mcp = pytest.importorskip("mcp")  # noqa: F841
        from adl_lite.mcp_server import create_mcp_server

        return create_mcp_server(state_path=str(tmp_path / "mcp_state.json"))

    @staticmethod
    def _tool(server, name: str):
        return server._tool_manager._tools[name].fn

    def test_private_doc_hidden_from_mcp_reads(self, mcp_server) -> None:
        reg = self._tool(mcp_server, "adl_register")
        reg(adl_id="mcp-priv", domain="test", scope="private/acme")
        reg(adl_id="mcp-pub", domain="test", scope="public")

        status = self._tool(mcp_server, "adl_status")
        assert "error" in status(adl_id="mcp-priv")
        assert status(adl_id="mcp-pub")["status"] == "provisional"

        listed = self._tool(mcp_server, "adl_list")()
        assert "mcp-pub" in listed["capabilities"]
        assert "mcp-priv" not in listed["capabilities"]

        history = self._tool(mcp_server, "adl_history")
        assert history(adl_id="mcp-priv") == []
        assert len(history(adl_id="mcp-pub")) >= 1

        verify = self._tool(mcp_server, "adl_verify")
        assert verify(adl_id="mcp-priv")["ok"] is False
        assert verify(adl_id="mcp-pub")["ok"] is True
