"""Unified experiment runner + CLI entry point.

python -m experiments.runner E2            # runs E2
python -m experiments.runner all           # runs all registered
python -m experiments.runner list          # list all
python -m experiments.runner E2 --verbose  # verbose output
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Import experiment modules so @register decorators fire
from . import (
    e1_chain_integrity,  # noqa: F401
    e2_status_derivation,  # noqa: F401
    e3_snapshot_roundtrip,  # noqa: F401
    e4_precondition,  # noqa: F401
    e5_agent_audit,  # noqa: F401
    e6_aml_pipeline,  # noqa: F401
    e6_multiagent_coordination,  # noqa: F401
    e7_realtime_watcher,  # noqa: F401
    e8_edge_sync,  # noqa: F401
    e9_git_baseline,  # noqa: F401
    e10_fde_pipeline,  # noqa: F401
    e11_sideeffect_stress,  # noqa: F401
    e12_benchmark_comparison,  # noqa: F401
    e13_longchain_stress,  # noqa: F401
    e14_colluding_validators,  # noqa: F401
    e15_precondition_boundary,  # noqa: F401
    e16_multiagent_contention,  # noqa: F401
    e19_governance_benchmark,  # noqa: F401
    e20_template_effectiveness,  # noqa: F401
    e20b_calibration_baseline,  # noqa: F401
    e21_100k_stress,  # noqa: F401
    e25_microbenchmark,  # noqa: F401
    E23_contention_stress,  # noqa: F401
    proof_trace_checker,  # noqa: F401
)
from .base import ExperimentResult
from .registry import instantiate, list_all

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "experiments"


def run_one(experiment_id: str) -> ExperimentResult:
    exp = instantiate(experiment_id)
    if exp is None:
        return ExperimentResult(
            experiment_id=experiment_id,
            status="failed",
            errors=[f"Unknown experiment: {experiment_id}"],
        )
    return exp._run_wrapper()


def run_all() -> dict[str, ExperimentResult]:
    results: dict[str, ExperimentResult] = {}
    for info in list_all():
        eid = info["id"]
        results[eid] = run_one(eid)
    return results


def write_summary(results: dict[str, ExperimentResult], path: Path | None = None) -> Path:
    out = path or OUTPUT_DIR / "experiment_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {experiment_id: r.to_dict() for experiment_id, r in results.items()}
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> None:
    args = _parse(argv)

    if args.command == "list":
        items = list_all()
        if not items:
            print("No experiments registered.")
            return
        for item in items:
            print(f"  {item['id']:6s}  {item['name']:40s}  {item['description']}")
        return

    run_ids: list[str]
    if args.command == "all":
        run_ids = [info["id"] for info in list_all()]
    else:
        run_ids = [args.command]

    results: dict[str, ExperimentResult] = {}
    for eid in run_ids:
        print(f"\n{'='*60}")
        print(f"  Running: {eid}")
        print(f"{'='*60}")
        result = run_one(eid)
        results[eid] = result
        _print_result(result, verbose=args.verbose)

    if results:
        summary_path = write_summary(results)
        print(f"\nSummary written: {summary_path}")

    failed = sum(1 for r in results.values() if r.status == "failed")
    if failed:
        sys.exit(1)


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ADL Lite experiment runner")
    parser.add_argument(
        "command",
        nargs="?",
        default="list",
        help="Experiment ID (E1..E5), 'all', or 'list' (default)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser.parse_args(argv)


def _print_result(result: ExperimentResult, verbose: bool = False) -> None:
    status_icon = {"passed": "PASS", "failed": "FAIL", "partial": "PART"}.get(
        result.status, result.status.upper()
    )
    print(f"\n  [{status_icon}] {result.experiment_id}  ({result.duration_ms}ms)")

    for k, v in result.metrics.items():
        print(f"    {k}: {v}")

    if result.errors:
        print(f"  Errors ({len(result.errors)}):")
        for e in result.errors[:5]:
            print(f"    - {e}")

    if verbose and result.raw_data:
        count = len(result.raw_data)
        print(f"  Raw data ({count} entries). First 3:")
        for item in result.raw_data[:3]:
            print(f"    {json.dumps(item, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
