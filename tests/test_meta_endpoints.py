"""M5 meta endpoints: task state machine + role whitelist single source of truth.

The meta endpoints serialize ``agents.task._TASK_TRANSITIONS`` and
``agents.roles.ROLE_SPECS`` so dashboards and runtime enforcement share one
source of truth. These tests pin the response shape (7 task statuses, the 5
runtime roles) so a future refactor cannot silently diverge.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from adl_lite.api import create_app


def _client() -> TestClient:
    """Return a TestClient backed by a fresh temp-state app instance."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        state_path = f.name
    app = create_app(state_path=state_path)
    tc = TestClient(app)
    Path(state_path).unlink(missing_ok=True)
    return tc


def test_task_transitions_meta() -> None:
    """All 7 task statuses are exported with their allowed targets."""
    tc = _client()
    resp = tc.get("/api/v1/meta/task-transitions")
    assert resp.status_code == 200
    body = resp.json()
    transitions = body["transitions"]

    assert set(transitions) == {
        "open",
        "assigned",
        "in_progress",
        "submitted",
        "validated",
        "rejected",
        "closed",
    }
    # open covers claim (in_progress) and close (closed).
    assert {"in_progress", "closed"} <= set(transitions["open"])
    assert set(transitions["submitted"]) == {"validated", "rejected"}
    # closed is terminal: no outgoing transitions.
    assert transitions["closed"] == []


def test_roles_meta() -> None:
    """The 5 runtime roles are exported with whitelists + policy."""
    tc = _client()
    resp = tc.get("/api/v1/meta/roles")
    assert resp.status_code == 200
    body = resp.json()
    roles = body["roles"]

    # Exactly the runtime roles — planner is a control-plane role, not a spec.
    assert set(roles) == {
        "discoverer",
        "reviewer",
        "skeptic",
        "merger",
        "librarian",
    }
    disc = roles["discoverer"]
    assert "adl_consensus_register" in disc["allowed_tools"]
    assert disc["validation_policy"] == "propose"
    assert disc["system_prompt"]
    # Every spec exposes the same envelope.
    for spec in roles.values():
        assert set(spec) == {"allowed_tools", "validation_policy", "system_prompt"}
        assert spec["allowed_tools"]
