"""
RQ1: Ambiguity reduction.

- pilot: legacy pronoun-rate with synthetic plain inflation (Phase 1)
- phase_b: paired fair plain baseline + rubric (no synthetic injection)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from adl_lite import parse_file
from adl_lite.validator import ADLValidator

from .baselines.fair_plain import adl_paths_to_fair_plain
from .rubric import compare_corpus

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
DATA = ROOT / "data" / "aml"

_FORBIDDEN = re.compile(
    r"\b(this|that|it|these|those|这个|那个|它|它们)\b",
    re.IGNORECASE,
)


def _collect_paths(paths: list[Path] | None) -> list[Path]:
    if paths is not None:
        return paths
    out = list(EXAMPLES.glob("*.md"))
    manifest = DATA / "manifest.json"
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for entry in data.get("concepts", []):
            p = DATA / entry["path"]
            if p.exists():
                out.append(p)
    return out


def run_pilot(paths: list[Path] | None = None) -> dict:
    """Legacy pilot metric (synthetic plain inflation)."""
    validator = ADLValidator()
    paths = _collect_paths(paths)
    adl_pronoun_hits = 0
    adl_words = 0
    plain_pronoun_hits = 0
    plain_words = 0

    for path in paths:
        doc = parse_file(path)
        body = doc.markdown_body.lower()
        words = len(body.split())
        adl_words += words
        adl_pronoun_hits += len(_FORBIDDEN.findall(body))
        errors = validator.validate_document(doc)
        adl_pronoun_hits += sum(1 for e in errors if "pronoun" in e.lower())

        plain = body + " this pattern shows that it works."
        plain_words += len(plain.split())
        plain_pronoun_hits += len(_FORBIDDEN.findall(plain))

    adl_rate = adl_pronoun_hits / max(adl_words, 1)
    plain_rate = plain_pronoun_hits / max(plain_words, 1)
    reduction = (plain_rate - adl_rate) / max(plain_rate, 1e-9)

    return {
        "metric": "pronoun_rate",
        "adl_rate": round(adl_rate, 4),
        "plain_baseline_rate": round(plain_rate, 4),
        "ambiguity_reduction_pct": round(reduction * 100, 2),
        "n_docs": len(paths),
        "pilot": True,
    }


def run_phase_b(paths: list[Path] | None = None) -> dict:
    """Phase B: rubric on paired ADL vs fair plain (same L2, no L3)."""
    paths = _collect_paths(paths)
    adl_docs = [parse_file(p) for p in paths]
    plain_docs = adl_paths_to_fair_plain(paths)
    result = compare_corpus(adl_docs, plain_docs)
    result["n_docs"] = len(paths)
    return result


def run(mode: str = "pilot", paths: list[Path] | None = None) -> dict:
    if mode == "phase_b":
        return run_phase_b(paths)
    return run_pilot(paths)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("pilot", "phase_b"), default="pilot")
    args = p.parse_args()
    print(json.dumps(run(mode=args.mode), indent=2))
