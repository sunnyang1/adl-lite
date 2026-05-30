"""
RQ1 human evaluation scaffold.

Loads rated discovery entries, computes mean referent clarity per comparison arm,
optional inter-rater stats, and writes a summary JSON for RESULTS.md.
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

ARM_FIELDS: dict[str, str] = {
    "adl_l2": "referent_clarity",
    "fair_plain_l2": "referent_clarity_fair_plain",
    "plain_llm_unstructured": "referent_clarity_plain_llm",
}


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


def _active_entries(entries: list[dict]) -> list[dict]:
    return [
        e
        for e in entries
        if e.get("adl_id") and (e.get("discovery_path") or "").strip()
    ]


def _arm_scores(entries: list[dict], field: str) -> list[float]:
    return [float(e[field]) for e in entries if e.get(field) is not None]


def _inter_rater_summary(
    entries: list[dict],
    *,
    primary_field: str = "referent_clarity",
    secondary_field: str = "referent_clarity_b",
    disagreement_threshold: int = 2,
) -> dict[str, Any]:
    pairs: list[tuple[float, float]] = []
    for entry in entries:
        a = entry.get(primary_field)
        b = entry.get(secondary_field)
        if a is None or b is None:
            continue
        pairs.append((float(a), float(b)))

    disagreements = sum(1 for a, b in pairs if abs(a - b) >= disagreement_threshold)
    out: dict[str, Any] = {
        "status": "pending",
        "icc_type": "ICC(2,k)",
        "icc": None,
        "n_pairs": len(pairs),
        "disagreement_threshold": disagreement_threshold,
        "disagreement_count": disagreements,
        "mean_absolute_difference": None,
    }
    if not pairs:
        out["status"] = "insufficient_data"
        return out

    out["mean_absolute_difference"] = round(
        sum(abs(a - b) for a, b in pairs) / len(pairs), 4
    )
    if len(pairs) < 2:
        out["status"] = "insufficient_data"
        return out

    # Placeholder: full ICC requires statsmodels/scipy; report agreement proxy only.
    out["status"] = "placeholder"
    out["note"] = (
        "ICC not computed in-tree; use n>=5 dual-rated items and export pairs "
        "to an external stats package for ICC(2,k)."
    )
    return out


def summarize(
    template: dict,
    *,
    plain_stub: dict[str, Any] | None = None,
) -> dict:
    """Compute human-eval summary from template entries."""
    entries: list[dict] = template.get("entries", [])
    active = _active_entries(entries)
    protocol = template.get("study_protocol", {})

    rated_adl = [e for e in active if e.get("referent_clarity") is not None]

    arms: dict[str, dict[str, Any]] = {}
    for arm_name, field in ARM_FIELDS.items():
        scores = _arm_scores(active, field)
        arms[arm_name] = {
            "field": field,
            "n_active": len(active),
            "n_rated": len(scores),
            "mean": _mean(scores),
        }

    adl_mean = arms["adl_l2"]["mean"]
    fair_mean = arms["fair_plain_l2"]["mean"]
    plain_mean = arms["plain_llm_unstructured"]["mean"]

    deltas: dict[str, float | None] = {
        "adl_minus_fair_plain": None,
        "adl_minus_plain_llm": None,
    }
    if adl_mean is not None and fair_mean is not None:
        deltas["adl_minus_fair_plain"] = round(adl_mean - fair_mean, 4)
    if adl_mean is not None and plain_mean is not None:
        deltas["adl_minus_plain_llm"] = round(adl_mean - plain_mean, 4)

    validator = ADLValidator()
    adl_ambiguity: list[float] = []
    plain_ambiguity: list[float] = []
    paired: list[dict] = []

    for entry in active:
        path_str = (entry.get("discovery_path") or "").strip()
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
                "referent_clarity_fair_plain": entry.get("referent_clarity_fair_plain"),
                "referent_clarity_plain_llm": entry.get("referent_clarity_plain_llm"),
                "validator_pass": len(val_errors) == 0,
                "adl_ambiguity": adl_score.ambiguity_score,
                "plain_ambiguity": plain_score.ambiguity_score,
            }
        )

    adl_amb_mean = _mean(adl_ambiguity)
    plain_amb_mean = _mean(plain_ambiguity)
    reduction_pct = None
    if adl_amb_mean is not None and plain_amb_mean is not None and plain_amb_mean > 0:
        reduction_pct = round((plain_amb_mean - adl_amb_mean) / plain_amb_mean * 100, 2)

    threshold = int(protocol.get("disagreement_threshold", 2))
    inter_rater = _inter_rater_summary(active, disagreement_threshold=threshold)

    out: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metric": "human_referent_clarity",
        "label": "Human inter-rater referent clarity (pending until raters score)",
        "n_entries": len(entries),
        "n_active_discoveries": len(active),
        "n_rated_adl": len(rated_adl),
        "comparison_arms": arms,
        "mean_deltas": deltas,
        "inter_rater": inter_rater,
        "validator_pass_count": sum(1 for e in active if e.get("validator_pass") is True),
        "n_with_discovery_files": len(paired),
        "adl_mean_ambiguity_rubric": adl_amb_mean,
        "fair_plain_mean_ambiguity_rubric": plain_amb_mean,
        "ambiguity_reduction_pct": reduction_pct,
        "paired_details": paired[:10],
        "llm_proxy_reference": "docs/experiments/rq1_llm_judge_summary.json",
    }

    # Back-compat keys used by older tests/docs.
    out["n_rated"] = len(rated_adl)
    out["mean_referent_clarity"] = adl_mean
    out["n_with_discovery"] = len(paired)
    out["adl_mean_ambiguity"] = adl_amb_mean
    out["plain_mean_ambiguity"] = plain_amb_mean

    if plain_stub:
        out["plain_stub"] = plain_stub
        stub_mean = plain_stub.get("mean_ambiguity")
        if stub_mean is not None and adl_amb_mean is not None:
            out["adl_vs_stub_delta"] = round(adl_amb_mean - float(stub_mean), 4)

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
