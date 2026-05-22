"""
CLI tests — subprocess invocation after editable install.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXAMPLES = ROOT / "examples"
INVALID = FIXTURES / "invalid_pronoun.md"
CAPITAL = EXAMPLES / "capital_reflux_trap.md"


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "adl_lite.cli", *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
    )


def test_help():
    proc = _run("--help")
    assert proc.returncode == 0
    assert "parse" in proc.stdout
    assert "validate" in proc.stdout
    assert "consensus" in proc.stdout


def test_parse_text_output():
    proc = _run("parse", str(CAPITAL))
    assert proc.returncode == 0
    assert "disc-capital-trap" in proc.stdout
    assert "relations:" in proc.stdout


def test_parse_json_output():
    proc = _run("parse", str(CAPITAL), "-o", "json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["front_matter"]["adl_id"] == "disc-capital-trap"


def test_validate_ok():
    proc = _run("validate", str(CAPITAL))
    assert proc.returncode == 0
    assert "OK" in proc.stdout


def test_validate_fails_on_invalid_pronoun():
    proc = _run("validate", str(INVALID))
    assert proc.returncode == 1
    assert "FAIL" in proc.stderr or "pronoun" in proc.stderr.lower()


def test_store_and_related(tmp_path: Path):
    db = tmp_path / "test.db"
    proc = _run("store", str(CAPITAL), "--db", str(db))
    assert proc.returncode == 0, proc.stderr

    proc = _run("related", "disc-capital-trap", "--db", str(db), "--depth", "2")
    assert proc.returncode == 0
    assert proc.stdout.strip() != ""


def test_consensus_register_transition_verify(tmp_path: Path):
    state = tmp_path / "consensus.json"
    proc = _run(
        "consensus",
        "register",
        str(CAPITAL),
        "--state",
        str(state),
    )
    assert proc.returncode == 0, proc.stderr

    proc = _run(
        "consensus",
        "transition",
        "disc-capital-trap",
        "--to",
        "validated",
        "--actor",
        "agent_reviewer",
        "--reason",
        "test approval",
        "--state",
        str(state),
    )
    assert proc.returncode == 0, proc.stderr

    proc = _run(
        "consensus",
        "verify",
        "disc-capital-trap",
        "--state",
        str(state),
    )
    assert proc.returncode == 0
    assert "chain OK" in proc.stdout


def test_validate_all_examples():
    paths = sorted(EXAMPLES.glob("*.md"))
    assert len(paths) >= 3
    proc = _run("validate", *[str(p) for p in paths])
    assert proc.returncode == 0, proc.stderr
