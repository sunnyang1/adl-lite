"""Tests for the `adl-lite neo4j` CLI commands and the compliance gate (T05).

The Neo4j driver is NOT installed in the test environment, so the "driver not
installed" degraded path is exercised by making ``Neo4jGraphAdapter._get_driver``
raise ``ImportError``. The success / connection-failure paths are exercised with a
mocked driver (no live Neo4j required).
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import adl_lite.neo4j_adapter as neo4j_mod
from adl_lite.cli import _cmd_neo4j_check, _cmd_neo4j_status

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _args() -> argparse.Namespace:
    return argparse.Namespace(uri="bolt://localhost:7687", user="neo4j", password="password")


def _raise_import_error(*_args: object, **_kwargs: object) -> object:
    raise ImportError(
        "Neo4j support requires the 'neo4j' extra. Install with: pip install adl-lite[neo4j]"
    )


def _good_driver(_self: object) -> MagicMock:
    """A driver whose node_count()/verify_connectivity() succeed."""
    driver = MagicMock(name="neo4j-driver")
    session = driver.session.return_value.__enter__.return_value
    record = MagicMock()
    record.__getitem__.return_value = 5
    session.run.return_value.single.return_value = record
    driver.verify_connectivity.return_value = True
    return driver


def _bad_driver(_self: object) -> MagicMock:
    """A driver whose session.run() raises (connection refused)."""
    driver = MagicMock(name="neo4j-driver-bad")
    session = driver.session.return_value.__enter__.return_value
    session.run.side_effect = RuntimeError("connection refused")
    driver.verify_connectivity.side_effect = RuntimeError("connection refused")
    return driver


def _false_driver(_self: object) -> MagicMock:
    """A driver whose verify_connectivity() raises (liveness fails).

    The adapter wraps ``driver.verify_connectivity()`` in a try/except and
    returns False on any exception, which is what the CLI interprets as a
    failed health check (exit 1).
    """
    driver = MagicMock(name="neo4j-driver-false")
    driver.verify_connectivity.side_effect = RuntimeError("server unreachable")
    return driver


# ---------------------------------------------------------------------------
# `neo4j status` — three exit paths
# ---------------------------------------------------------------------------


class TestNeo4jStatus:
    def test_status_degraded_no_driver(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(neo4j_mod.Neo4jGraphAdapter, "_get_driver", _raise_import_error):
            rc = _cmd_neo4j_status(_args())
        assert rc == 1
        assert "Neo4j driver not installed" in capsys.readouterr().err

    def test_status_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(neo4j_mod.Neo4jGraphAdapter, "_get_driver", _good_driver):
            rc = _cmd_neo4j_status(_args())
        assert rc == 0
        out = capsys.readouterr().out
        assert "Neo4j connection OK" in out
        assert "Nodes: 5" in out

    def test_status_connection_failure(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(neo4j_mod.Neo4jGraphAdapter, "_get_driver", _bad_driver):
            rc = _cmd_neo4j_status(_args())
        assert rc == 1
        assert "Neo4j connection FAILED" in capsys.readouterr().err

    def test_status_degraded_via_subprocess(self) -> None:
        """End-to-end: `adl-lite neo4j status` degrades gracefully (exit 1)."""
        result = subprocess.run(
            [sys.executable, "-m", "adl_lite.cli", "neo4j", "status"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        # No live Neo4j and (likely) no driver -> graceful non-zero exit.
        assert result.returncode == 1


# ---------------------------------------------------------------------------
# `neo4j check` — three exit paths
# ---------------------------------------------------------------------------


class TestNeo4jCheck:
    def test_check_degraded_no_driver(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(neo4j_mod.Neo4jGraphAdapter, "_get_driver", _raise_import_error):
            rc = _cmd_neo4j_check(_args())
        assert rc == 1
        assert "Neo4j driver not installed" in capsys.readouterr().err

    def test_check_ok(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(neo4j_mod.Neo4jGraphAdapter, "_get_driver", _good_driver):
            rc = _cmd_neo4j_check(_args())
        assert rc == 0
        assert "Neo4j health check OK" in capsys.readouterr().out

    def test_check_connectivity_false(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(neo4j_mod.Neo4jGraphAdapter, "_get_driver", _false_driver):
            rc = _cmd_neo4j_check(_args())
        assert rc == 1
        assert "connectivity verification returned False" in capsys.readouterr().err

    def test_check_connection_exception(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(neo4j_mod.Neo4jGraphAdapter, "_get_driver", _bad_driver):
            rc = _cmd_neo4j_check(_args())
        assert rc == 1
        assert "Neo4j health check FAILED" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Compliance gate (scripts/check_compliance_ready.py)
# ---------------------------------------------------------------------------


def _load_compliance_module():
    path = REPO_ROOT / "scripts" / "check_compliance_ready.py"
    spec = importlib.util.spec_from_file_location("check_compliance_ready", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestComplianceReady:
    def test_extra_declares_tomllib(self) -> None:
        mod = _load_compliance_module()
        text = (
            '[project]\nname="x"\n'
            "[project.optional-dependencies]\n"
            'neo4j=["neo4j>=5.0"]\n'
            'experiments=["pygit2>=1.12", "prov>=2.0.0"]\n'
        )
        assert mod._extra_declares(text, "neo4j", "neo4j>=5.0") is True
        assert mod._extra_declares(text, "experiments", "pygit2>=1.12") is True

    def test_extra_declares_missing_dependency(self) -> None:
        mod = _load_compliance_module()
        text = (
            '[project]\nname="x"\n[project.optional-dependencies]\nneo4j=["something-else>=1.0"]\n'
        )
        assert mod._extra_declares(text, "neo4j", "neo4j>=5.0") is False

    def test_compliance_ready_passes(self) -> None:
        """The real project state must satisfy the production-gate checks."""
        result = subprocess.run(
            [sys.executable, "scripts/check_compliance_ready.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr

    def test_compliance_ready_fails_on_violation(self, tmp_path: Path) -> None:
        """A tampered pyproject (missing neo4j>=5.0) must fail the gate."""
        mod = _load_compliance_module()
        bad = tmp_path / "pyproject.toml"
        bad.write_text(
            '[project]\nname="x"\n'
            "[project.optional-dependencies]\n"
            'neo4j=["old-neo4j>=1.0"]\n'
            'experiments=["pygit2>=1.12"]\n',
            encoding="utf-8",
        )
        original = mod.PYPROJECT
        mod.PYPROJECT = bad
        try:
            assert mod.main() == 1
        finally:
            mod.PYPROJECT = original
