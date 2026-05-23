"""Run Phase B evaluation (fair baselines, TF-IDF, optional LLM sim)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from . import rq1_ambiguity, rq2_consensus, rq3_retrieval, rq4_leakage
from .llm_harness import run_llm_sim, write_llm_log

RESULTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "experiments"


def run_phase_b(*, llm: bool = False) -> dict:
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": "B",
        "pilot": False,
        "rq1_ambiguity": rq1_ambiguity.run(mode="phase_b"),
        "rq2_consensus": rq2_consensus.run(),
        "rq3_retrieval": rq3_retrieval.run(mode="phase_b"),
        "rq4_leakage": rq4_leakage.run(),
    }

    if llm:
        llm_result = run_llm_sim()
        summary["llm_sim"] = llm_result.to_dict()
        if llm_result.events:
            write_llm_log(llm_result)

    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run ADL Lite Phase B evaluation")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Include optional LLM 5-agent discoverer (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Write summary JSON (default: docs/experiments/summary_phase_b.json)",
    )
    args = parser.parse_args(argv)

    summary = run_phase_b(llm=args.llm)
    out = Path(args.out) if args.out else RESULTS_DIR / "summary_phase_b.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
