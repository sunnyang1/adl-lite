#!/usr/bin/env python3
"""ADL Lite paper compression checker.

Counts lines in each .tex file under docs/paper_ao/sections/ and
supplementary/, reports the main body total vs the 850-line target,
and writes JSON/CSV reports.
"""

import csv
import json
import sys
from pathlib import Path
from typing import cast

SECTIONS_DIR = Path("docs/paper_ao/sections")
SUPPLEMENTARY_DIR = Path("docs/paper_ao/supplementary")
TARGET_LINES = 850

# Files that are \input into main.tex (the paper body)
MAIN_BODY_FILES = [
    "abstract.tex",
    "01_introduction.tex",
    "02_related_work.tex",
    "03_ontological_analysis.tex",
    "04_architecture.tex",
    "05_empirical_validation.tex",
    "06_discussion.tex",
    "07_conclusion.tex",
]


def count_lines(path: Path) -> int:
    """Return total line count (including blank lines) for a file."""
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def analyze_directory(directory: Path, label: str) -> dict:
    """Analyze all .tex files in a directory."""
    files = sorted(directory.glob("*.tex"))
    entries = []
    total = 0
    for file in files:
        n = count_lines(file)
        total += n
        entries.append(
            {
                "file": file.name,
                "lines": n,
                "category": label,
            }
        )
    return {
        "entries": entries,
        "total_lines": total,
    }


def print_report(body: dict, existing: dict, supplementary: dict) -> None:
    """Print a human-readable report to stdout."""
    print("=" * 60)
    print("ADL Lite Paper Compression Report")
    print("=" * 60)
    print()
    print(f"{'Main body file':<40} {'Lines':>6}")
    print("-" * 48)
    for entry in body["entries"]:
        print(f"{entry['file']:<40} {entry['lines']:>6}")
    print("-" * 48)
    print(f"{'TOTAL (main body)':<40} {body['total_lines']:>6}")
    print(f"{'TARGET':<40} {TARGET_LINES:>6}")
    overage = body["total_lines"] - TARGET_LINES
    print(f"{'OVERAGE':<40} {overage:>6}")
    print(f"{'% of target':<40} {round(body['total_lines'] / TARGET_LINES * 100, 1):>6}")
    print()

    print("-" * 48)
    print(f"{'Existing appendix file':<40} {'Lines':>6}")
    print("-" * 48)
    for entry in existing["entries"]:
        print(f"{entry['file']:<40} {entry['lines']:>6}")
    print("-" * 48)
    print(f"{'TOTAL (existing appendices)':<40} {existing['total_lines']:>6}")
    print()

    print("-" * 48)
    print(f"{'Supplementary file':<40} {'Lines':>6}")
    print("-" * 48)
    for entry in supplementary["entries"]:
        print(f"{entry['file']:<40} {entry['lines']:>6}")
    print("-" * 48)
    print(f"{'TOTAL (supplementary)':<40} {supplementary['total_lines']:>6}")
    print()

    grand_total = body["total_lines"] + existing["total_lines"] + supplementary["total_lines"]
    print(f"{'GRAND TOTAL (all .tex)':<40} {grand_total:>6}")
    print()

    if body["total_lines"] <= TARGET_LINES:
        print("✅ Target achieved: main body is within the 850-line limit.")
    else:
        print(f"⚠️  Target NOT achieved: main body exceeds limit by {overage} lines.")
    print("=" * 60)


def write_json(body: dict, existing: dict, supplementary: dict, path: Path) -> None:
    """Write combined report as JSON."""
    report = {
        "main_body": body,
        "existing_appendices": existing,
        "supplementary": supplementary,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"JSON report written to: {path}")


def write_csv(body: dict, existing: dict, supplementary: dict, path: Path) -> None:
    """Write combined report as CSV."""
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "file", "lines", "target", "overage"])
        for entry in body["entries"]:
            writer.writerow(["main_body", entry["file"], entry["lines"], TARGET_LINES, ""])
        writer.writerow(
            [
                "main_body",
                "TOTAL",
                body["total_lines"],
                TARGET_LINES,
                body["total_lines"] - TARGET_LINES,
            ]
        )
        for entry in existing["entries"]:
            writer.writerow(["existing_appendix", entry["file"], entry["lines"], "", ""])
        writer.writerow(["existing_appendix", "TOTAL", existing["total_lines"], "", ""])
        for entry in supplementary["entries"]:
            writer.writerow(["supplementary", entry["file"], entry["lines"], "", ""])
        writer.writerow(["supplementary", "TOTAL", supplementary["total_lines"], "", ""])
    print(f"CSV report written to: {path}")


def main() -> int:
    # Analyze main body files explicitly
    body_entries = []
    body_total = 0
    for name in MAIN_BODY_FILES:
        file = SECTIONS_DIR / name
        n = count_lines(file)
        body_total += n
        body_entries.append({"file": file.name, "lines": n, "category": "main_body"})
    body = {"entries": body_entries, "total_lines": body_total}

    existing = analyze_directory(SECTIONS_DIR, "existing_appendix")
    # Remove main body entries from existing so we don't double-count
    existing["entries"] = [e for e in existing["entries"] if e["file"] not in MAIN_BODY_FILES]
    existing["total_lines"] = sum(e["lines"] for e in existing["entries"])

    supplementary = analyze_directory(SUPPLEMENTARY_DIR, "supplementary")

    print_report(body, existing, supplementary)

    write_json(body, existing, supplementary, Path("docs/paper_ao/compression_report.json"))
    write_csv(body, existing, supplementary, Path("docs/paper_ao/compression_report.csv"))

    return 0 if cast(int, body["total_lines"]) <= TARGET_LINES else 1


if __name__ == "__main__":
    sys.exit(main())
