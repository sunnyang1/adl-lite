"""End-to-end demo pipeline tests (scripted path, no API)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "demo_pipeline.py"
SHELL = ROOT / "scripts" / "demo_pipeline.sh"


def _is_bundled_python_codesign_issue() -> bool:
    """Detect the pydantic_core code-signing issue in WorkBuddy's bundled Python.

    Checks both the current process and the default 'python' on PATH (used by shell wrappers).
    """
    # Check current process
    try:
        from adl_lite.models import Event  # noqa: F401
    except ImportError:
        return True

    # Check if 'python' on PATH has the issue (relevant for shell wrapper tests)
    import shutil

    python_bin = shutil.which("python")
    if python_bin and ".workbuddy" in str(python_bin):
        return True
    return False


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


_has_codesign_issue = _is_bundled_python_codesign_issue()


def test_scripted_pipeline_end_to_end(tmp_path: Path):
    db = tmp_path / "demo.db"
    proc = _run("--scripted", "--db", str(db))
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert db.exists()
    assert "ADL Lite Demo Pipeline" in proc.stdout
    assert "disc-capital-trap" in proc.stdout
    assert "Stored" in proc.stdout
    assert "isomorphic-to" in proc.stdout or "related concept" in proc.stdout.lower()


def test_scripted_pipeline_default_mode(tmp_path: Path):
    db = tmp_path / "demo_default.db"
    proc = _run("--db", str(db))
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "Mode:      scripted" in proc.stdout


def test_scripted_sim_mode(tmp_path: Path):
    db = tmp_path / "demo_sim.db"
    proc = _run("--scripted", "--sim", "--db", str(db))
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "scripted-sim" in proc.stdout
    assert "Sim log:" in proc.stdout


def test_llm_skips_without_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MIMO_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    db = tmp_path / "demo_llm.db"
    proc = _run("--llm", "--db", str(db))
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "skipped" in proc.stdout.lower()


@pytest.mark.skipif(_has_codesign_issue, reason="Bundled Python pydantic_core code-signing issue")
def test_shell_wrapper(tmp_path: Path):
    db = tmp_path / "demo_sh.db"
    proc = subprocess.run(
        [str(SHELL), "--scripted", "--db", str(db)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "disc-capital-trap" in proc.stdout
