"""Tests for scripts/run_tlc.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

# Import scripts/run_tlc.py without requiring scripts/ to be a package.
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("run_tlc", _SCRIPTS_DIR / "run_tlc.py")
assert spec is not None and spec.loader is not None
run_tlc_module = importlib.util.module_from_spec(spec)
sys.modules["run_tlc"] = run_tlc_module
spec.loader.exec_module(run_tlc_module)


build_config = run_tlc_module.build_config
main = run_tlc_module.main
run_tlc = run_tlc_module.run_tlc
SPEC_CONFIGS = run_tlc_module.SPEC_CONFIGS


@pytest.mark.parametrize("spec_name", list(SPEC_CONFIGS))
def test_build_config_contains_constants_and_invariants(spec_name: str) -> None:
    """Each spec config must declare the universal constants and its invariants."""
    cfg = build_config(
        spec=spec_name,
        actors=["alice", "bob"],
        max_events=5,
        max_confidence=10,
        n_min=2 if spec_name == "ConsensusEngine" else None,
    )
    assert "Actors =" in cfg
    assert "MaxEvents = 5" in cfg
    assert "MaxConfidence = 10" in cfg
    assert "INIT Init" in cfg
    assert "NEXT Next" in cfg
    for inv in SPEC_CONFIGS[spec_name]["invariants"]:
        assert f"INVARIANT {inv}" in cfg


def test_build_config_requires_n_min_for_consensus() -> None:
    """ConsensusEngine config generation fails without N_min."""
    with pytest.raises(ValueError, match="requires --n-min"):
        build_config(
            spec="ConsensusEngine",
            actors=["alice"],
            max_events=5,
            max_confidence=10,
            n_min=None,
        )


def test_build_config_rejects_unknown_spec() -> None:
    """An unsupported spec name must raise a clear error."""
    with pytest.raises(ValueError, match="Unknown spec"):
        build_config(
            spec="NonExistent",
            actors=["alice"],
            max_events=5,
            max_confidence=10,
        )


@pytest.mark.parametrize(
    ("argv", "expected_spec"),
    [
        ([], "EventChain"),
        (["--spec", "CRDTMerge"], "CRDTMerge"),
        (["--spec", "ConsensusEngine", "--n-min", "2"], "ConsensusEngine"),
    ],
)
def test_main_argument_parsing(argv: list[str], expected_spec: str) -> None:
    """main() must parse CLI arguments and forward them to run_tlc()."""
    with mock.patch.object(run_tlc_module, "run_tlc", return_value=0) as mock_run:
        result = main(argv)
    assert result == 0
    assert mock_run.call_args is not None
    assert mock_run.call_args.kwargs["spec"] == expected_spec


def test_main_default_invocation_matches_eventchain() -> None:
    """Calling main() without arguments keeps the original EventChain default."""
    with mock.patch.object(run_tlc_module, "run_tlc", return_value=0) as mock_run:
        main([])
    kwargs = mock_run.call_args.kwargs
    assert kwargs["spec"] == "EventChain"
    assert kwargs["max_events"] == 10
    assert kwargs["max_confidence"] == 10
    assert kwargs["actors"] == ["alice", "bob"]


def test_run_tlc_returns_one_when_tlc_missing(capsys: pytest.CaptureFixture[str]) -> None:
    """If TLC is not available, run_tlc returns 1 and prints a helpful message."""
    with mock.patch.object(run_tlc_module, "_resolve_tlc", return_value=None):
        result = run_tlc(
            spec="EventChain",
            max_events=5,
            max_confidence=10,
        )
    assert result == 1
    captured = capsys.readouterr()
    assert "TLC not found" in captured.out


def test_run_tlc_returns_one_when_spec_missing(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """If the requested spec file does not exist, run_tlc returns 1."""
    with (
        mock.patch.object(run_tlc_module, "_resolve_tlc", return_value="/fake/tlc"),
        mock.patch.object(run_tlc_module, "SPEC_DIR", tmp_path),
    ):
        result = run_tlc(spec="EventChain", max_events=5, max_confidence=10)
    assert result == 1
    captured = capsys.readouterr()
    assert "Spec file not found" in captured.out


@pytest.mark.skipif(run_tlc_module._resolve_tlc() is None, reason="TLC not installed")
def test_run_tlc_invokes_tlc_for_eventchain(tmp_path: Path) -> None:
    """When TLC is present, run_tlc builds a config and invokes it."""
    result = run_tlc(
        spec="EventChain",
        max_events=2,
        max_confidence=1,
        actors=["alice"],
    )
    assert result == 0
