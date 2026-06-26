#!/usr/bin/env python3
"""
Wrapper to run TLC on ADL Lite TLA+ specs with configurable bounds.

TLC must be installed separately (e.g. via the TLA+ Toolbox or a community
package). This script generates a temporary MC.cfg and invokes:

    tlc -config MC.cfg -workers N <Spec>.tla

Example:
    python scripts/run_tlc.py --spec EventChain --max-events 20 --max-confidence 100
    python scripts/run_tlc.py --spec CRDTMerge --workers 4
    python scripts/run_tlc.py --spec ConsensusEngine --n-min 2
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SPEC_DIR = Path(__file__).resolve().parent.parent / "specs"
LOCAL_TLC = Path(__file__).resolve().parent.parent / "tools" / "tla+" / "tlc"

SPEC_CONFIGS: dict[str, dict[str, list[str]]] = {
    "EventChain": {
        "invariants": [
            "Inv_WellFormednessPreserved",
            "Inv_StatusMonotonic",
            "Inv_MonotonicAppend",
        ],
        "extra_constants": [],
    },
    "CRDTMerge": {
        "invariants": [
            "Inv_MergedWellFormed",
            "Inv_MergedStatusConfidence",
            "Inv_MergeCommutative",
            "Inv_MergeIdempotent",
            "Inv_MergeAssociative",
        ],
        "extra_constants": [],
    },
    "ConsensusEngine": {
        "invariants": [
            "Inv_WellFormednessPreserved",
            "Inv_ValidTransition",
            "Inv_MinValidators",
            "Inv_StatusMonotonic",
            "Inv_ConfidenceBounded",
        ],
        "extra_constants": ["N_min"],
    },
}


def build_config(
    spec: str,
    actors: list[str],
    max_events: int,
    max_confidence: int,
    n_min: int | None = None,
) -> str:
    """Return the contents of a TLC configuration file for the chosen spec."""
    if spec not in SPEC_CONFIGS:
        raise ValueError(f"Unknown spec: {spec}. Choose from {list(SPEC_CONFIGS)}.")

    quoted_actors = ", ".join(f'"{a}"' for a in actors)
    lines = [
        "CONSTANTS",
        f"  Actors = {{{quoted_actors}}}",
        f"  MaxEvents = {max_events}",
        f"  MaxConfidence = {max_confidence}",
    ]
    if "N_min" in SPEC_CONFIGS[spec]["extra_constants"]:
        if n_min is None:
            raise ValueError(f"Spec {spec} requires --n-min to be set.")
        lines.append(f"  N_min = {n_min}")
    lines.extend(["", "INIT Init", "NEXT Next", ""])
    for inv in SPEC_CONFIGS[spec]["invariants"]:
        lines.append(f"INVARIANT {inv}")
    return "\n".join(lines) + "\n"


def _resolve_tlc() -> str | None:
    """Return the TLC executable, falling back to the project-local wrapper."""
    tlc = shutil.which("tlc")
    if tlc is not None:
        return tlc
    if LOCAL_TLC.exists() and os.access(LOCAL_TLC, os.X_OK):
        return str(LOCAL_TLC)
    return None


def run_tlc(
    spec: str,
    max_events: int,
    max_confidence: int,
    actors: list[str] | None = None,
    n_min: int | None = None,
    workers: int | None = None,
) -> int:
    tlc = _resolve_tlc()
    if tlc is None:
        print("TLC not found. Please install TLA+ Tools and ensure 'tlc' is on PATH.")
        return 1

    actors = actors or ["alice", "bob"]
    spec_file = SPEC_DIR / f"{spec}.tla"
    if not spec_file.exists():
        print(f"Spec file not found: {spec_file}")
        return 1

    config = build_config(spec, actors, max_events, max_confidence, n_min=n_min)
    with tempfile.TemporaryDirectory(prefix="adl_tlc_") as tmp:
        cfg_path = Path(tmp) / "MC.cfg"
        cfg_path.write_text(config, encoding="utf-8")
        cmd = [tlc, "-deadlock", "-config", str(cfg_path)]
        if workers is not None and workers > 1:
            cmd.extend(["-workers", str(workers)])
        cmd.append(str(spec_file))
        print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, cwd=SPEC_DIR)
        return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run TLC on ADL Lite TLA+ specs")
    parser.add_argument(
        "--spec",
        choices=list(SPEC_CONFIGS),
        default="EventChain",
        help="TLA+ spec to model check (default: EventChain)",
    )
    parser.add_argument("--max-events", type=int, default=10)
    parser.add_argument("--max-confidence", type=int, default=10)
    parser.add_argument("--actors", nargs="+", default=["alice", "bob"])
    parser.add_argument(
        "--n-min",
        type=int,
        default=None,
        help="Minimum distinct validators required by ConsensusEngine (required for that spec)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of TLC worker threads (passed as -workers N when > 1)",
    )
    args = parser.parse_args(argv)
    return run_tlc(
        spec=args.spec,
        max_events=args.max_events,
        max_confidence=args.max_confidence,
        actors=args.actors,
        n_min=args.n_min,
        workers=args.workers,
    )


if __name__ == "__main__":
    sys.exit(main())
