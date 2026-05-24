#!/usr/bin/env python3
"""Smoke test: parse, strict-validate, store, and index AML concepts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adl_lite import parse_file
from adl_lite.validator import ADLValidator
from data.aml.loader import index_all

DATA = ROOT / "data" / "aml"
CONCEPTS = DATA / "concepts"
SAMPLE_IDS = ["aml-smurfing", "aml-layering", "aml-fan-in-pattern"]


def main() -> int:
    errors: list[str] = []
    validator = ADLValidator(strict=True)

    for stem in SAMPLE_IDS:
        path = CONCEPTS / f"{stem}.md"
        if not path.exists():
            errors.append(f"missing {path}")
            continue
        doc = parse_file(path)
        v_errors = validator.validate_document(doc)
        if v_errors:
            errors.append(f"strict validate failed: {path}: {v_errors}")

    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    expected = manifest.get("count", 0)
    if expected != len(manifest.get("concepts", [])):
        errors.append("manifest count mismatch")

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "aml_smoke.db"
        mem = index_all(db)
        if mem.retrieve("aml-smurfing") is None:
            errors.append("retrieve(aml-smurfing) failed after index_all")
        if len(mem.hot) != expected:
            errors.append(f"hot index size {len(mem.hot)} != manifest count {expected}")
        mem.close()

    proc = subprocess.run(
        [sys.executable, str(DATA / "scripts" / "validate_corpus.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        errors.append(f"validate_corpus: {proc.stdout}\n{proc.stderr}")

    if errors:
        for e in errors:
            print("FAIL:", e, file=sys.stderr)
        return 1

    print("OK: smoke test passed for", ", ".join(SAMPLE_IDS))
    print(f"OK: indexed {expected} concepts via index_all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
