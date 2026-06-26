#!/usr/bin/env python3
"""
Paper–code consistency check script.

Verifies that the LaTeX paper and the Python codebase remain aligned after
the CRDT migration and other breaking changes.

Checks:
  1. No "last-write-wins" or "LWW" residue in paper sections
  2. All experiment IDs referenced in paper exist in code
  3. All registered experiment IDs are unique
  4. Theorem numbers (T1–T9) have corresponding test files
  5. StatusOrder in crdt.py matches _cached_status_order in models.py

Usage:
    python scripts/consistency_check.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def check_paper_no_lww_residue(paper_dir: Path) -> list[str]:
    """Check that paper sections contain no 'last-write-wins' or standalone 'LWW'."""
    errors = []
    for tex_file in paper_dir.rglob("*.tex"):
        content = tex_file.read_text()
        # Allow "LWW-Set" (used in CRDT merge description) but flag plain "LWW"
        for match in re.finditer(r"\b[Ll]ast[-\s]?write[-\s]?wins\b|\bLWW\b(?!-Set)", content):
            line_num = content[: match.start()].count("\n") + 1
            errors.append(
                f"  {tex_file.relative_to(paper_dir.parent)}:{line_num}: found '{match.group()}'"
            )
    return errors


def check_experiment_ids_unique(experiments_dir: Path) -> list[str]:
    """Check that all @register("E...") IDs are unique."""
    errors = []
    seen: dict[str, Path] = {}
    for py_file in list(experiments_dir.glob("e*.py")) + list(experiments_dir.glob("E*.py")):
        content = py_file.read_text()
        for match in re.finditer(r'@register\("(E\d+\w?)"\)', content):
            eid = match.group(1)
            if eid in seen:
                errors.append(
                    f"  Duplicate experiment ID '{eid}' in "
                    f"{py_file.name} (first seen in {seen[eid].name})"
                )
            else:
                seen[eid] = py_file
    return errors


def check_paper_experiments_exist(paper_dir: Path, experiments_dir: Path) -> list[str]:
    """Check that experiment IDs mentioned in paper have corresponding modules."""
    errors = []
    # Collect all registered experiment IDs from code
    registered: set[str] = set()
    for py_file in list(experiments_dir.glob("e*.py")) + list(experiments_dir.glob("E*.py")):
        content = py_file.read_text()
        for match in re.finditer(r'@register\("(E\d+\w?)"\)', content):
            registered.add(match.group(1))

    # Scan paper for experiment references like E1, E2, E25, E6b
    for tex_file in paper_dir.rglob("*.tex"):
        content = tex_file.read_text()
        for match in re.finditer(r"\b(E\d+\w?)\b", content):
            eid = match.group(1)
            if eid not in registered:
                # Whitelist common false positives
                if eid in {
                    "E1",
                    "E2",
                    "E3",
                    "E4",
                    "E5",
                    "E6",
                    "E7",
                    "E8",
                    "E9",
                    "E10",
                    "E11",
                    "E12",
                    "E13",
                    "E14",
                    "E15",
                    "E16",
                    "E17",
                    "E18",
                    "E19",
                    "E20",
                    "E20b",
                    "E21",
                    "E22",
                    "E23",
                    "E24",
                    "E25",
                }:
                    line_num = content[: match.start()].count("\n") + 1
                    errors.append(
                        f"  {tex_file.relative_to(paper_dir.parent)}:{line_num}: "
                        f"paper references '{eid}' but no experiment module registers it"
                    )
    return errors


def check_theorem_tests(tests_dir: Path) -> list[str]:
    """Check that theorem numbers T1–T9 have corresponding test files or mentions."""
    errors = []
    test_files = {f.name for f in tests_dir.glob("test_theorem*.py")}
    expected = {
        "T1": "test_theorem_t1.py",
        "T2": "test_theorem_t2.py",
        "T3": "test_theorem_t3.py",
        "T4": "test_theorem_t4.py",
        "T5": "test_theorem_t5.py",
        "T6": "test_theorem_t6.py",
        "T7": "test_theorem_t7.py",
        "T8": "test_theorem_t8.py",
        "T9": "test_theorem_t9.py",
    }
    # We have some theorems covered in test_theorems.py (combined) and some in individual files
    combined = (tests_dir / "test_theorems.py").exists()
    for theorem, expected_file in expected.items():
        if expected_file not in test_files and not combined:
            errors.append(f"  Missing test coverage for {theorem}")
    # T6 is known to be in test_theorem_t6.py
    if not (tests_dir / "test_theorem_t6.py").exists():
        errors.append("  Missing test_theorem_t6.py")
    return errors


def check_status_order_consistency(repo_root: Path) -> list[str]:
    """Check that StatusOrder in crdt.py matches the cache logic in models.py."""
    errors = []
    crdt_path = repo_root / "adl_lite" / "crdt.py"
    models_path = repo_root / "adl_lite" / "models.py"

    crdt_content = crdt_path.read_text()
    models_content = models_path.read_text()

    # Extract StatusOrder enum values from crdt.py
    status_order_entries = dict(re.findall(r"(\w+) = (\d+)", crdt_content))
    expected_order = ["PROVISIONAL", "FORKED", "VALIDATED", "DEPRECATED", "ARCHIVED"]
    for i, name in enumerate(expected_order, start=1):
        if status_order_entries.get(name) != str(i):
            errors.append(
                f"  StatusOrder.{name} expected {i}, got {status_order_entries.get(name)}"
            )

    # Check that models.py uses the same order in _update_crdt_caches
    for event_type, status_name in [
        ("REGISTER", "PROVISIONAL"),
        ("VALIDATE", "VALIDATED"),
        ("DEPRECATE", "DEPRECATED"),
        ("FORK", "FORKED"),
        ("ARCHIVE", "ARCHIVED"),
    ]:
        if f"EventType.{event_type}: DiscoveryStatus.{status_name}" not in models_content:
            errors.append(
                f"  models.py _update_crdt_caches missing mapping {event_type} -> {status_name}"
            )

    return errors


def main() -> int:
    repo_root = Path(__file__).parent.parent
    paper_dir = repo_root / "docs" / "paper_ao"
    experiments_dir = repo_root / "experiments"
    tests_dir = repo_root / "tests"

    print("=" * 60)
    print(" ADL Lite — Paper / Code Consistency Check ".center(60))
    print("=" * 60)

    all_errors: list[str] = []

    # 1. LWW residue
    print("\n[1/5] Checking for 'last-write-wins' / 'LWW' residue in paper...")
    errs = check_paper_no_lww_residue(paper_dir)
    if errs:
        print("  FAIL:")
        for e in errs:
            print(e)
        all_errors.extend(errs)
    else:
        print("  PASS — no LWW residue found")

    # 2. Unique experiment IDs
    print("\n[2/5] Checking experiment ID uniqueness...")
    errs = check_experiment_ids_unique(experiments_dir)
    if errs:
        print("  FAIL:")
        for e in errs:
            print(e)
        all_errors.extend(errs)
    else:
        print("  PASS — all experiment IDs unique")

    # 3. Paper references exist
    print("\n[3/5] Checking paper experiment references exist in code...")
    errs = check_paper_experiments_exist(paper_dir, experiments_dir)
    if errs:
        print("  FAIL:")
        for e in errs:
            print(e)
        all_errors.extend(errs)
    else:
        print("  PASS — all referenced experiments exist")

    # 4. Theorem tests
    print("\n[4/5] Checking theorem test coverage...")
    errs = check_theorem_tests(tests_dir)
    if errs:
        print("  FAIL:")
        for e in errs:
            print(e)
        all_errors.extend(errs)
    else:
        print("  PASS — theorem tests present")

    # 5. StatusOrder consistency
    print("\n[5/5] Checking StatusOrder / cache consistency...")
    errs = check_status_order_consistency(repo_root)
    if errs:
        print("  FAIL:")
        for e in errs:
            print(e)
        all_errors.extend(errs)
    else:
        print("  PASS — StatusOrder and cache logic consistent")

    # Summary
    print("\n" + "=" * 60)
    if all_errors:
        print(
            f" RESULT: {len(all_errors)} issue(s) found — please fix before submission ".center(60)
        )
        print("=" * 60)
        return 1
    else:
        print(" RESULT: ALL CHECKS PASSED ✓ ".center(60))
        print("=" * 60)
        return 0


if __name__ == "__main__":
    sys.exit(main())
