#!/usr/bin/env python3
"""Validate all AML concept files with adl-lite strict semantics."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONCEPTS = ROOT / "data" / "aml" / "concepts"


def main() -> int:
    paths = sorted(CONCEPTS.glob("aml-*.md"))
    if not paths:
        print("No concept files found", file=sys.stderr)
        return 1
    cmd = ["adl-lite", "validate", "--strict", *[str(p) for p in paths]]
    print("Running:", " ".join(cmd[:4]), f"... ({len(paths)} files)")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        return result.returncode
    failed = [line for line in result.stdout.splitlines() if ": OK" not in line and line.strip()]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
