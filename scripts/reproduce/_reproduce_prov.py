"""Reproduce PROV-O export for all example concepts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from adl_lite.parser import parse_file  # noqa: E402
from adl_lite.prov_export import to_prov_o, validate_turtle  # noqa: E402


def main():
    examples_dir = PROJECT_ROOT / "examples"
    artifacts_dir = PROJECT_ROOT / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    results = []
    all_valid = True

    for md_file in sorted(examples_dir.glob("*.md")):
        try:
            doc = parse_file(md_file)
            ttl = to_prov_o(doc.event_chain)
            valid = validate_turtle(ttl)
            out_path = artifacts_dir / f"{md_file.stem}.ttl"
            out_path.write_text(ttl)
            results.append(
                {
                    "file": md_file.name,
                    "concept_id": doc.adl_id,
                    "valid_turtle": valid,
                    "output": str(out_path.relative_to(PROJECT_ROOT)),
                }
            )
            if not valid:
                all_valid = False
        except Exception as e:
            results.append(
                {
                    "file": md_file.name,
                    "concept_id": None,
                    "valid_turtle": False,
                    "error": str(e),
                }
            )
            all_valid = False

    with open(artifacts_dir / "prov_export_report.json", "w") as f:
        json.dump(results, f, indent=2)

    for r in results:
        status = "PASS" if r.get("valid_turtle") else "FAIL"
        print(f"  {status}: {r['file']} -> {r.get('output', r.get('error'))}")

    passed = sum(1 for r in results if r.get("valid_turtle"))
    print(f"\nPROV-O Export: {passed}/{len(results)} valid")
    print("OVERALL: PASS" if all_valid else "OVERALL: FAIL")
    return 0 if all_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
