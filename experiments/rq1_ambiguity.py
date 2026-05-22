"""
RQ1: Ambiguity reduction — pronoun / fuzzy referent rate in L2 body.

Pilot metric on scripted corpus (synthetic baseline comparison).
"""

from __future__ import annotations

import re
from pathlib import Path

from adl_lite import parse_file
from adl_lite.validator import ADLValidator

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"

_FORBIDDEN = re.compile(
    r"\b(this|that|it|these|those|这个|那个|它|它们)\b",
    re.IGNORECASE,
)


def ambiguity_score(paths: list[Path]) -> dict:
    """Lower pronoun rate = lower ambiguity (ADL goal)."""
    validator = ADLValidator()
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


def run(paths: list[Path] | None = None) -> dict:
    paths = paths or list(EXAMPLES.glob("*.md"))
    return ambiguity_score(paths)


if __name__ == "__main__":
    import json

    print(json.dumps(run(), indent=2))
