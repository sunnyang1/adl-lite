"""
RQ2 LLM batch consensus analysis — run N LLM sims and compare to scripted baseline.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import rq2_consensus
from .harness import SimEvent
from .llm_harness import LLMSimResult, run_llm_sim, write_llm_log

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = Path(__file__).resolve().parent / "logs" / "llm_run.jsonl"
SUMMARY_PATH = ROOT / "docs" / "experiments" / "rq2_llm_summary.json"


def _mean_std(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "std": None}
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return {"mean": mean, "std": std}


def parse_llm_log(path: Path) -> list[dict[str, Any]]:
    """Extract result dicts from llm_run.jsonl (one per sim run)."""
    if not path.exists():
        return []

    results: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "result" in row:
            results.append(row["result"])
    return results


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(results)
    if n == 0:
        return {
            "n_runs": 0,
            "consensus_transitions": {"mean": None, "std": None},
            "success_rate": None,
            "mean_attempts": None,
            "revised_rate": None,
        }

    transitions = [float(r.get("consensus_transitions", 0)) for r in results]
    attempts = [float(r.get("attempts", 1)) for r in results]
    completed = sum(1 for r in results if r.get("status") == "completed")
    revised = sum(1 for r in results if r.get("revised"))

    return {
        "n_runs": n,
        "consensus_transitions": _mean_std(transitions),
        "success_rate": completed / n,
        "mean_attempts": statistics.mean(attempts),
        "revised_rate": revised / n,
    }


def mock_llm_result(
    *,
    status: str = "completed",
    consensus_transitions: int = 2,
    attempts: int = 1,
    revised: bool = False,
) -> LLMSimResult:
    """Deterministic sim result for dry-run / tests (no API)."""
    events = [
        SimEvent(1, "discoverer", "emit_llm", "pending", {"attempt": 1}),
        SimEvent(2, "discoverer", "parsed", "disc-llm-peripheral-trap", {"attempt": attempts}),
        SimEvent(3, "reviewer", "validate", "disc-llm-peripheral-trap", {"ok": status == "completed"}),
    ]
    if status == "completed":
        events.append(
            SimEvent(4, "reviewer", "transition", "disc-llm-peripheral-trap", {"to": "validated"}),
        )
    return LLMSimResult(
        status=status,
        events=events,
        detail={
            "consensus_transitions": consensus_transitions if status == "completed" else 0,
            "provider": "mock",
            "model": "mock",
            "attempts": attempts,
            "revised": revised,
        },
    )


def run_batch(
    *,
    n: int = 10,
    dry_run: bool = False,
    log_path: Path | None = None,
    append_log: bool = True,
) -> list[dict[str, Any]]:
    """Run N LLM sims (or mocks) and optionally append to log."""
    log = log_path or LOG_PATH
    results: list[dict[str, Any]] = []

    for i in range(n):
        if dry_run:
            # Vary mock outcomes slightly for meaningful aggregates
            revised = i % 3 == 1
            attempts = 2 if revised else 1
            status = "completed" if i % 5 != 4 else "validation_failed"
            sim = mock_llm_result(
                status=status,
                consensus_transitions=2 if status == "completed" else 0,
                attempts=attempts,
                revised=revised,
            )
        else:
            sim = run_llm_sim()
            if sim.status == "skipped":
                raise RuntimeError(
                    "LLM unavailable. Use --dry-run or set MIMO_API_KEY / OPENAI_API_KEY."
                )

        result_dict = sim.to_dict()
        results.append(result_dict)

        if append_log:
            mode = "a" if log.exists() and i > 0 else "w"
            log.parent.mkdir(parents=True, exist_ok=True)
            lines = [json.dumps({"result": result_dict}, sort_keys=True)]
            for e in sim.events:
                lines.append(e.to_json())
            with log.open(mode, encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

    return results


def build_summary(
    llm_results: list[dict[str, Any]],
    *,
    log_path: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Aggregate LLM runs and compare to scripted RQ2 baseline."""
    llm_agg = aggregate_results(llm_results)
    scripted = rq2_consensus.run()

    llm_mean = llm_agg["consensus_transitions"]["mean"]
    scripted_transitions = scripted["adl_transitions"]
    delta = None
    if llm_mean is not None and not (isinstance(llm_mean, float) and math.isnan(llm_mean)):
        delta = llm_mean - scripted_transitions

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": "B",
        "rq": "RQ2",
        "dry_run": dry_run,
        "log_path": str(log_path or LOG_PATH),
        "llm": llm_agg,
        "scripted_baseline": {
            "consensus_transitions": scripted_transitions,
            "adl_validated_count": scripted["adl_validated_count"],
            "baseline_transitions": scripted["baseline_transitions"],
            "n_docs": scripted["n_docs"],
        },
        "comparison": {
            "llm_mean_transitions": llm_mean,
            "scripted_transitions": scripted_transitions,
            "delta_llm_minus_scripted": delta,
        },
    }


def analyze_log(path: Path | None = None) -> dict[str, Any]:
    """Parse existing log and produce summary."""
    log = path or LOG_PATH
    results = parse_llm_log(log)
    return build_summary(results, log_path=log)


def write_summary(summary: dict[str, Any], out: Path | None = None) -> Path:
    target = out or SUMMARY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="RQ2 LLM batch consensus analysis")
    parser.add_argument("--n", type=int, default=10, help="Number of LLM sim runs (default: 10)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use mock results without calling LLM API",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Parse existing experiments/logs/llm_run.jsonl only",
    )
    parser.add_argument(
        "--log",
        default=None,
        help="Path to llm_run.jsonl (default: experiments/logs/llm_run.jsonl)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Write summary JSON (default: docs/experiments/rq2_llm_summary.json)",
    )
    args = parser.parse_args(argv)

    log_path = Path(args.log) if args.log else LOG_PATH

    if args.analyze_only:
        summary = analyze_log(log_path)
    else:
        results = run_batch(n=args.n, dry_run=args.dry_run, log_path=log_path)
        summary = build_summary(results, log_path=log_path, dry_run=args.dry_run)

    out = write_summary(summary, Path(args.out) if args.out else None)
    print(json.dumps(summary, indent=2))
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
