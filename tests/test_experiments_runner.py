"""Tests for the experiment runner's graceful degradation (T04).

Acceptance criteria verified here:
    * ``python -m experiments.runner list`` does not crash in a clean env
      (no pygit2 / prov / rdflib installed).
    * ``all`` is runnable (the runner degrades a single broken experiment to a
      failed result instead of crashing the whole process).
    * E19 is listed and annotated as *unavailable* when its optional deps
      (pygit2, prov, rdflib) are missing.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

_E19_OPTIONAL_DEPS = frozenset({"pygit2", "rdflib", "prov"})


@pytest.fixture
def hide_e19_deps(monkeypatch: pytest.MonkeyPatch):
    """Make E19's optional deps (pygit2 / rdflib / prov) look uninstalled.

    Both ``E19GovernanceBenchmark.is_available()`` and ``_require_e19_deps()``
    resolve availability via ``importlib.util.find_spec`` (imported inside the
    functions, i.e. looked up on the ``importlib.util`` module at call time),
    so patching that attribute covers every call site regardless of whether
    the host environment actually has the packages installed.
    """
    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str, package: str | None = None):
        if name.split(".")[0] in _E19_OPTIONAL_DEPS:
            return None
        return real_find_spec(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    return fake_find_spec


def test_module_imports_without_optional_deps() -> None:
    """Importing the runner must not require pygit2 / prov / rdflib."""
    import experiments.runner  # noqa: F401

    assert experiments.runner is not None


def test_list_command_does_not_crash() -> None:
    """``python -m experiments.runner list`` returns 0 in a clean environment."""
    result = subprocess.run(
        [sys.executable, "-m", "experiments.runner", "list"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr


def test_e19_registered_and_marked_unavailable(hide_e19_deps) -> None:
    """E19 must be registered and report is_available() == False without pygit2."""
    from experiments.registry import instantiate, list_all

    ids = {item["id"] for item in list_all()}
    assert "E19" in ids

    exp = instantiate("E19")
    assert exp is not None
    # pygit2 / prov / rdflib are hidden by the hide_e19_deps fixture, so E19
    # reports unavailable regardless of the host environment.
    assert exp.is_available() is False


def test_run_one_e19_graceful_failure(hide_e19_deps) -> None:
    """Running E19 without its optional deps degrades to a failed result."""
    from experiments.runner import run_one

    result = run_one("E19")
    assert result.status == "failed"
    assert result.errors  # a descriptive error (missing optional deps)
    assert any("pygit2" in e or "experiments" in e for e in result.errors)


def test_run_one_unknown_experiment_is_failed_result() -> None:
    """An unknown experiment id yields a failed result, not an exception."""
    from experiments.runner import run_one

    result = run_one("NONEXISTENT_XYZ_999")
    assert result.status == "failed"
    assert result.errors
    assert "Unknown experiment" in result.errors[0]


def test_run_one_wraps_runtime_errors() -> None:
    """A runtime failure inside run() is captured into a failed result."""

    from experiments.base import BaseExperiment, ExperimentResult
    from experiments.registry import register
    from experiments.runner import run_one

    @register("E_TEST_WRAP")
    class _Boom(BaseExperiment):
        experiment_id = "E_TEST_WRAP"
        name = "boom"
        description = "boom"

        def run(self) -> ExperimentResult:
            raise RuntimeError("kaboom")

    result = run_one("E_TEST_WRAP")
    assert result.status == "failed"
    assert any("kaboom" in e for e in result.errors)


def test_list_annotates_e19_unavailable(hide_e19_deps, capsys: pytest.CaptureFixture[str]) -> None:
    """The `list` command annotates E19 as unavailable when deps are missing."""
    from experiments.runner import main

    main(["list"])
    out = capsys.readouterr().out
    assert "E19" in out
    # Missing-deps annotation (pygit2/rdflib/prov hidden by the fixture):
    assert "unavailable: missing optional dependencies" in out
