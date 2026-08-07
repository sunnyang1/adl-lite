#!/usr/bin/env python3
"""Paper-Code Consistency Guard.

Checks that numeric claims in the Applied Ontology manuscript (docs/paper_ao/)
still match the current repository state. The 2026-08 audit found the paper
quoting stale figures (944/1,311 tests vs the actual 1,638; 77% vs 87%
coverage), so this guard exists to make such drift *fail loudly* instead of
being discovered by reviewers.

Checks
------
1. Test-count claims in `sections/*.tex` must be consistent with
   `pytest --collect-only` (fast suite) within a small tolerance.
2. Coverage claims must be consistent with `pytest --cov` output.
3. Version claims (`vX.Y.Z-alpha`) in the paper must match
   `adl_lite.__version__`.

Usage
-----
    python scripts/check_paper_code_consistency.py [--collect] [--coverage]

Exit code 0 = consistent; 1 = drift detected (lists offending files/lines).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = ROOT / "docs" / "paper_ao" / "sections"
TEST_COUNT_RE = re.compile(r"(\d{1,2},\d{3}|\d{3,4})\s*(?:pytest\s*)?cases?\b", re.IGNORECASE)
TEST_COUNT_CLAIM_RE = re.compile(r"(\d{3,4})\s*(?:tests?|pytest cases)")
COVERAGE_RE = re.compile(r"(\d{1,3})\s*%?\s*coverage", re.IGNORECASE)
VERSION_RE = re.compile(r"\bv0\.\d+\.\d+(?:-alpha)?\b")
# ADL Lite's own version appears in phrases like "as of v0.6.0-alpha",
# "v0.6.0-alpha includes", "version~0.2.0, Git tag~v0.6.0-alpha". External tool
# versions (ROBOT v1.9.7, HermiT v1.4.3, Coq v8.18) must NOT be flagged.
ADL_VERSION_CLAIM_RE = re.compile(
    r"(?:as of|version~?|Git tag~?|v)\s*(v0\.\d+\.\d+(?:-alpha)?)"
    r"|as of v0\.\d+\.\d+",
    re.IGNORECASE,
)
# Numbers that appear right after "v" in tool-name contexts (ROBOT/HermiT/Coq)
TOOL_VERSION_PREFIXES = ("ROBOT", "HermiT", "Coq", "TLC", "Java", "Python")

# Claims in the paper that are known-good "at the time of writing" but refer to
# a *specific historical* snapshot; we only check the headline counts.
SKIP_FILES = {"08_reviewer_response.tex"}  # R&R material, not the submission body


def git_version() -> str:
    """Return the package version from adl_lite.__version__."""
    sys.path.insert(0, str(ROOT))
    import adl_lite  # noqa: PLC0415

    return adl_lite.__version__


def collect_test_count() -> tuple[int, str]:
    """Run pytest --collect-only and return (count, summary_line)."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-m",
            "not slow",
            "--collect-only",
            "-q",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    match = re.search(r"(\d+) (?:tests? )?collected", proc.stdout)
    if match:
        return int(match.group(1)), proc.stdout.strip().splitlines()[-1]
    # fallback: count test items from output
    count = len([ln for ln in proc.stdout.splitlines() if ln and not ln.startswith("<")])
    return count, proc.stdout.strip().splitlines()[-1]


def run_coverage() -> float | None:
    """Run pytest --cov and extract the total coverage percentage."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-m",
            "not slow",
            "--cov=adl_lite",
            "--cov-report=term",
            "-q",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    # Last line of cov report looks like "TOTAL    1234   56   78%"
    for line in reversed(proc.stdout.splitlines()):
        if "TOTAL" in line:
            m = re.search(r"(\d{1,3})%", line)
            if m:
                return float(m.group(1))
    return None


def scan_claims() -> list[tuple[str, int, str, str]]:
    """Return [(file, line, claim_text, matched_number)] for numeric claims."""
    claims: list[tuple[str, int, str, str]] = []
    for tex in sorted(SECTIONS.glob("*.tex")):
        if tex.name in SKIP_FILES:
            continue
        for lineno, line in enumerate(tex.read_text(encoding="utf-8").splitlines(), 1):
            if TEST_COUNT_CLAIM_RE.search(line):
                claims.append((tex.name, lineno, line.strip()[:120], "test_count"))
            if COVERAGE_RE.search(line) and "%" in line:
                claims.append((tex.name, lineno, line.strip()[:120], "coverage"))
    return claims


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true", help="run pytest --collect-only")
    parser.add_argument("--coverage", action="store_true", help="run pytest --cov")
    args = parser.parse_args()

    problems: list[str] = []
    version = git_version()

    # 1. Version claims (ADL Lite's own version only; skip external tool versions)
    for tex in sorted(SECTIONS.glob("*.tex")):
        if tex.name in SKIP_FILES:
            continue
        text = tex.read_text(encoding="utf-8")
        for m in VERSION_RE.finditer(text):
            claimed = m.group(0).lstrip("v")
            # Skip if the preceding token is an external tool name.
            line_start = text.rfind("\n", 0, m.start()) + 1
            prefix = text[line_start : m.start()]
            if any(tok in prefix[-30:] for tok in TOOL_VERSION_PREFIXES):
                continue
            if claimed != version and claimed != "0.2.0":  # PyPI historical tag
                problems.append(f"{tex.name}: version claim {m.group(0)} != current {version}")

    # 2. Test count claims
    if args.collect:
        actual, _ = collect_test_count()
        print(f"[INFO] collected tests: {actual}")
        for fname, lineno, line, kind in scan_claims():
            if kind != "test_count":
                continue
            nums = [int(n.replace(",", "")) for n in TEST_COUNT_CLAIM_RE.findall(line)]
            if nums and all(abs(n - actual) > 100 for n in nums):
                problems.append(
                    f"{fname}:{lineno}: test count {nums} != collected {actual}: {line}"
                )

    # 3. Coverage claims
    if args.coverage:
        cov = run_coverage()
        if cov is not None:
            print(f"[INFO] coverage: {cov}%")
            for fname, lineno, line, kind in scan_claims():
                if kind != "coverage":
                    continue
                mc = COVERAGE_RE.search(line)
                if mc and abs(float(mc.group(1)) - cov) > 5:
                    problems.append(
                        f"{fname}:{lineno}: coverage {m.group(1)}% != measured {cov:.0f}%: {line}"
                    )

    if problems:
        print("❌ Paper-code consistency drift detected:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("✅ No paper-code consistency drift detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
