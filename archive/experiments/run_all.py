"""Run all RQ pilot experiments and write summary JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from . import rq1_ambiguity, rq2_consensus, rq3_retrieval, rq4_leakage

RESULTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "experiments"


def run_all() -> dict:
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pilot": True,
        "rq1_ambiguity": rq1_ambiguity.run(),
        "rq2_consensus": rq2_consensus.run(),
        "rq3_retrieval": rq3_retrieval.run(),
        "rq4_leakage": rq4_leakage.run(),
    }
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run ADL Lite evaluation")
    parser.add_argument(
        "--phase",
        choices=("pilot", "b"),
        default="pilot",
        help="pilot=Phase 1 metrics; b=Phase B fair baselines + TF-IDF",
    )
    parser.add_argument("--db", default=None, help="Optional AML db path (unused in pilot)")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="With --phase b: run optional LLM discoverer (OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Write summary JSON (default: docs/experiments/summary.json or summary_phase_b.json)",
    )
    args = parser.parse_args(argv)

    if args.phase == "b":
        from .run_phase_b import run_phase_b

        summary = run_phase_b(llm=args.llm)
        default_out = RESULTS_DIR / "summary_phase_b.json"
    else:
        summary = run_all()
        default_out = RESULTS_DIR / "summary.json"

    out = Path(args.out) if args.out else default_out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
