"""
RQ1 human evaluation scaffold.

Loads rated discovery entries, computes mean referent clarity, and compares
ADL discoveries against optional fair-plain rubric scores.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adl_lite import parse_file
from adl_lite.validator import ADLValidator

from .baselines.fair_plain import adl_to_fair_plain
from .rubric import score_document

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "data" / "eval" / "human_rq1_template.json"
DEFAULT_OUTPUT = ROOT / "docs" / "experiments" / "rq1_human_summary.json"


def load_template(path: Path | None = None) -> dict:
    p = path or DEFAULT_TEMPLATE
    return json.loads(p.read_text(encoding="utf-8"))


def _resolve_path(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def summarize(
    template: dict,
    *,
    plain_stub: dict[str, Any] | None = None,
) -> dict:
    """Compute human-eval summary from template entries."""
    entries: list[dict] = template.get("entries", [])
    rated = [e for e in entries if e.get("referent_clarity") is not None]

    validator = ADLValidator()
    adl_ambiguity: list[float] = []
    plain_ambiguity: list[float] = []
    paired: list[dict] = []

    for entry in entries:
        path_str = (entry.get("discovery_path") or "").strip()
        if not path_str:
            continue
        p = _resolve_path(path_str)
        if not p.exists():
            continue

        adl_doc = parse_file(p)
        plain_doc = adl_to_fair_plain(p)
        adl_score = score_document(adl_doc)
        plain_score = score_document(plain_doc)
        adl_ambiguity.append(adl_score.ambiguity_score)
        plain_ambiguity.append(plain_score.ambiguity_score)

        val_errors = validator.validate_document(adl_doc)
        paired.append(
            {
                "adl_id": entry.get("adl_id") or adl_doc.adl_id,
                "discovery_path": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
                "referent_clarity": entry.get("referent_clarity"),
                "validator_pass": len(val_errors) == 0,
                "adl_ambiguity": adl_score.ambiguity_score,
                "plain_ambiguity": plain_score.ambiguity_score,
            }
        )

    adl_mean = _mean(adl_ambiguity)
    plain_mean = _mean(plain_ambiguity)
    reduction_pct = None
    if adl_mean is not None and plain_mean is not None and plain_mean > 0:
        reduction_pct = round((plain_mean - adl_mean) / plain_mean * 100, 2)

    out: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metric": "human_referent_clarity",
        "n_entries": len(entries),
        "n_rated": len(rated),
        "mean_referent_clarity": _mean([float(e["referent_clarity"]) for e in rated]),
        "validator_pass_count": sum(1 for e in entries if e.get("validator_pass") is True),
        "n_with_discovery": len(paired),
        "adl_mean_ambiguity": adl_mean,
        "plain_mean_ambiguity": plain_mean,
        "ambiguity_reduction_pct": reduction_pct,
        "paired_details": paired[:10],
    }

    if plain_stub:
        out["plain_stub"] = plain_stub
        stub_mean = plain_stub.get("mean_ambiguity")
        if stub_mean is not None and adl_mean is not None:
            out["adl_vs_stub_delta"] = round(adl_mean - float(stub_mean), 4)

    return out


def run(
    template_path: Path | None = None,
    output_path: Path | None = None,
    *,
    plain_stub_path: Path | None = None,
) -> dict:
    template = load_template(template_path)
    plain_stub = None
    if plain_stub_path and plain_stub_path.exists():
        plain_stub = json.loads(plain_stub_path.read_text(encoding="utf-8"))

    summary = summarize(template, plain_stub=plain_stub)
    out = output_path or DEFAULT_OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["output_path"] = str(out)
    return summary


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="RQ1 human referent clarity summary")
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE),
        help="Path to human eval template JSON",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT),
        help="Write summary JSON (default: docs/experiments/rq1_human_summary.json)",
    )
    parser.add_argument(
        "--plain-stub",
        default=None,
        help="Optional JSON with precomputed plain baseline scores",
    )
    args = parser.parse_args(argv)

    summary = run(
        template_path=Path(args.template),
        output_path=Path(args.out),
        plain_stub_path=Path(args.plain_stub) if args.plain_stub else None,
    )
    print(json.dumps(summary, indent=2))
    print(f"\nwritten: {summary['output_path']}")


if __name__ == "__main__":
    main()
