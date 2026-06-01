"""Reproduce SHACL validation over exported PROV-O Turtle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from adl_lite.shacl_validation import validate_adl_rdf  # noqa: E402


def main():
    artifacts_dir = PROJECT_ROOT / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    ttl_files = list(artifacts_dir.glob("*.ttl"))
    results = []
    all_conform = True

    for ttl_file in ttl_files:
        rdf_data = ttl_file.read_text()
        conforms, report = validate_adl_rdf(rdf_data)
        results.append(
            {
                "file": ttl_file.name,
                "conforms": conforms,
                "report": report if not conforms else "Valid",
            }
        )
        if not conforms:
            all_conform = False

    with open(artifacts_dir / "shacl_validation_report.json", "w") as f:
        json.dump(results, f, indent=2)

    for r in results:
        status = "PASS" if r["conforms"] else "FAIL"
        print(f"  {status}: {r['file']}")

    passed = sum(1 for r in results if r["conforms"])
    print(f"\nSHACL Validation: {passed}/{len(results)} conform")
    print("OVERALL: PASS" if all_conform else "OVERALL: FAIL")
    return 0 if all_conform else 1


if __name__ == "__main__":
    raise SystemExit(main())
