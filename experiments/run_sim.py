"""Run scripted 5-agent simulation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .harness import run_scripted_sim


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="ADL Lite scripted 5-agent simulation")
    parser.add_argument(
        "--scripted",
        action="store_true",
        help="Run deterministic scripted scenario (default mode)",
    )
    parser.add_argument("--db", default=":memory:", help="SQLite path for librarian index")
    parser.add_argument(
        "--log",
        default=None,
        help="Output JSONL log path (default: experiments/logs/run_001.jsonl)",
    )
    args = parser.parse_args(argv)

    if not args.scripted:
        print("Only --scripted mode is supported in v0.1", file=sys.stderr)
        raise SystemExit(1)

    log_path = Path(args.log) if args.log else None
    out = run_scripted_sim(db_path=args.db, log_path=log_path)
    print(f"scripted sim complete: {len(out.read_text().splitlines())} events -> {out}")


if __name__ == "__main__":
    main()
