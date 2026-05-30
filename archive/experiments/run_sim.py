"""Run scripted 5-agent simulation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import json

from .harness import run_scripted_sim


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="ADL Lite 5-agent simulation")
    parser.add_argument(
        "--scripted",
        action="store_true",
        help="Run deterministic scripted scenario",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Run LLM discoverer + reviewer (MIMO_API_KEY or OPENAI_API_KEY)",
    )
    parser.add_argument("--db", default=":memory:", help="SQLite path for librarian index")
    parser.add_argument(
        "--log",
        default=None,
        help="Output JSONL log path",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model override (default: mimo-v2.5-pro or gpt-4o-mini by provider)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="On validate/parse failure, ask LLM to revise this many times (default: 1)",
    )
    args = parser.parse_args(argv)

    if args.llm:
        from .llm_harness import run_llm_sim, write_llm_log

        result = run_llm_sim(model=args.model, max_retries=args.max_retries)
        log_path = Path(args.log) if args.log else None
        if result.events:
            out = write_llm_log(result, log_path)
            print(f"llm sim: {result.status} -> {out}")
        else:
            print(json.dumps(result.to_dict(), indent=2))
        if result.status == "skipped":
            raise SystemExit(0)
        raise SystemExit(0 if result.status == "completed" else 1)

    if not args.scripted:
        print("Use --scripted or --llm", file=sys.stderr)
        raise SystemExit(1)

    log_path = Path(args.log) if args.log else None
    out = run_scripted_sim(db_path=args.db, log_path=log_path)
    print(f"scripted sim complete: {len(out.read_text().splitlines())} events -> {out}")


if __name__ == "__main__":
    main()
