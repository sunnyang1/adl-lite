"""
RQ1 LLM-as-judge referent clarity (OpenAI + Claude).

Scores L2 markdown only — separate providers from MiMo discoverer.
Label results as LLM-as-judge, not human evaluation.

Usage:
  python -m experiments.rq1_llm_judge --all --judges openai,claude
  python -m experiments.rq1_llm_judge --discovery experiments/outputs/llm_discovery_peripheral-trap.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adl_lite import parse_file

from .baselines.fair_plain import adl_to_fair_plain
from .judge_clients import (
    JudgeProvider,
    anthropic_judge_config,
    judge_chat,
    openai_judge_config,
    parse_judge_response,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "data" / "eval" / "human_rq1_template.json"
DEFAULT_SUMMARY = ROOT / "docs" / "experiments" / "rq1_llm_judge_summary.json"
JUDGE_PROMPT_PATH = ROOT / "prompts" / "judge_referent_clarity.md"

FIELD_OPENAI = "llm_judge_openai"
FIELD_CLAUDE = "llm_judge_claude"
FIELD_OPENAI_PLAIN = "llm_judge_openai_plain"
FIELD_CLAUDE_PLAIN = "llm_judge_claude_plain"
DISAGREEMENT_THRESHOLD = 2


def load_template(path: Path | None = None) -> dict:
    p = path or DEFAULT_TEMPLATE
    return json.loads(p.read_text(encoding="utf-8"))


def save_template(template: dict, path: Path | None = None) -> None:
    p = path or DEFAULT_TEMPLATE
    p.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")


def load_judge_prompt() -> str:
    return JUDGE_PROMPT_PATH.read_text(encoding="utf-8")


def _resolve_path(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def l2_body_from_path(path: Path, *, plain: bool = False) -> str:
    if plain:
        doc = adl_to_fair_plain(path)
    else:
        doc = parse_file(path)
    return doc.markdown_body.strip()


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def judge_text(
    l2_text: str,
    provider: JudgeProvider,
    *,
    system_prompt: str | None = None,
    chat_fn: Any = None,
) -> dict[str, Any]:
    """Call judge; return {score, model, rationale}."""
    system = system_prompt or load_judge_prompt()
    chat = chat_fn or judge_chat
    if provider == "openai":
        cfg = openai_judge_config()
    else:
        cfg = anthropic_judge_config()
    if not cfg:
        raise RuntimeError(f"{provider} API not configured")
    _key, model = cfg
    raw = chat(provider, system, l2_text)
    parsed = parse_judge_response(raw)
    return {
        "score": parsed["referent_clarity"],
        "model": model,
        "rationale": parsed["rationale"],
    }


def entries_with_discovery(template: dict) -> list[dict]:
    out: list[dict] = []
    for entry in template.get("entries", []):
        path_str = (entry.get("discovery_path") or "").strip()
        if path_str:
            out.append(entry)
    return out


def run_judges_for_entry(
    entry: dict,
    providers: list[JudgeProvider],
    *,
    include_plain: bool = True,
    system_prompt: str | None = None,
    chat_fn: Any = None,
) -> dict[str, Any]:
    path = _resolve_path(entry["discovery_path"])
    if not path.exists():
        raise FileNotFoundError(path)

    adl_l2 = l2_body_from_path(path, plain=False)
    plain_l2 = l2_body_from_path(path, plain=True) if include_plain else None

    row: dict[str, Any] = {
        "adl_id": entry.get("adl_id"),
        "discovery_path": entry.get("discovery_path"),
        "judges": {},
        "skipped": [],
    }

    for provider in providers:
        field = FIELD_OPENAI if provider == "openai" else FIELD_CLAUDE
        try:
            result = judge_text(adl_l2, provider, system_prompt=system_prompt, chat_fn=chat_fn)
            entry[field] = result
            entry[f"referent_clarity_{provider}"] = result["score"]
            row["judges"][provider] = {"adl": result}
        except RuntimeError as e:
            row["skipped"].append({"provider": provider, "reason": str(e)})
            continue

        if include_plain and plain_l2 is not None:
            plain_field = FIELD_OPENAI_PLAIN if provider == "openai" else FIELD_CLAUDE_PLAIN
            try:
                plain_result = judge_text(
                    plain_l2, provider, system_prompt=system_prompt, chat_fn=chat_fn
                )
                entry[plain_field] = plain_result
                row["judges"][provider]["plain"] = plain_result
            except Exception as e:
                row["judges"][provider]["plain_error"] = str(e)

    openai_score = entry.get(FIELD_OPENAI, {}).get("score") if isinstance(entry.get(FIELD_OPENAI), dict) else None
    claude_score = entry.get(FIELD_CLAUDE, {}).get("score") if isinstance(entry.get(FIELD_CLAUDE), dict) else None
    if openai_score is not None and claude_score is not None:
        row["judge_disagreement"] = abs(int(openai_score) - int(claude_score)) >= DISAGREEMENT_THRESHOLD

    return row


def build_summary(template: dict, run_rows: list[dict]) -> dict[str, Any]:
    entries = entries_with_discovery(template)
    providers_present: set[str] = set()
    for row in run_rows:
        for p in row.get("judges", {}):
            providers_present.add(p)

    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metric": "llm_referent_clarity",
        "label": "LLM-as-judge (not human evaluation)",
        "n_discoveries": len(entries),
        "disagreement_threshold": DISAGREEMENT_THRESHOLD,
        "per_judge": {},
        "entries": run_rows,
    }

    per_judge_means: list[float] = []
    disagreement_count = 0

    for provider in ("openai", "claude"):
        field = FIELD_OPENAI if provider == "openai" else FIELD_CLAUDE
        plain_field = FIELD_OPENAI_PLAIN if provider == "openai" else FIELD_CLAUDE_PLAIN
        adl_scores: list[float] = []
        plain_scores: list[float] = []
        deltas: list[float] = []
        model_name = None

        for entry in entries:
            obj = entry.get(field)
            if not isinstance(obj, dict) or obj.get("score") is None:
                continue
            adl_scores.append(float(obj["score"]))
            model_name = obj.get("model") or model_name
            plain_obj = entry.get(plain_field)
            if isinstance(plain_obj, dict) and plain_obj.get("score") is not None:
                plain_scores.append(float(plain_obj["score"]))
                deltas.append(float(obj["score"]) - float(plain_obj["score"]))

        if adl_scores:
            providers_present.add(provider)
            pj: dict[str, Any] = {
                "model": model_name,
                "n_scored": len(adl_scores),
                "mean_adl": _mean(adl_scores),
            }
            if plain_scores:
                pj["mean_plain"] = _mean(plain_scores)
                pj["mean_delta_adl_minus_plain"] = _mean(deltas)
            summary["per_judge"][provider] = pj
            if pj["mean_adl"] is not None:
                per_judge_means.append(float(pj["mean_adl"]))

    for row in run_rows:
        if row.get("judge_disagreement"):
            disagreement_count += 1

    summary["judges_scored"] = sorted(providers_present)
    summary["mean_across_judges_adl"] = _mean(per_judge_means) if per_judge_means else None
    summary["disagreement_count"] = disagreement_count

    skipped_all: list[str] = []
    for row in run_rows:
        for s in row.get("skipped", []):
            skipped_all.append(s.get("provider", "?"))
    summary["judges_skipped"] = sorted(set(skipped_all))

    return summary


def run(
    *,
    template_path: Path | None = None,
    summary_path: Path | None = None,
    discovery: Path | None = None,
    all_discoveries: bool = False,
    judges: list[JudgeProvider] | None = None,
    include_plain: bool = True,
    write_template: bool = True,
    system_prompt: str | None = None,
    chat_fn: Any = None,
) -> dict[str, Any]:
    template = load_template(template_path)
    providers: list[JudgeProvider] = judges or ["openai", "claude"]

    targets = entries_with_discovery(template)
    if discovery:
        rel = str(discovery.relative_to(ROOT)) if discovery.is_relative_to(ROOT) else str(discovery)
        targets = [e for e in targets if e.get("discovery_path") == rel or _resolve_path(e["discovery_path"]) == discovery]
        if not targets:
            targets = [{"discovery_path": rel, "adl_id": None}]
    elif not all_discoveries and not discovery:
        raise ValueError("specify --discovery PATH or --all")

    run_rows: list[dict] = []
    for entry in targets:
        run_rows.append(
            run_judges_for_entry(
                entry,
                providers,
                include_plain=include_plain,
                system_prompt=system_prompt,
                chat_fn=chat_fn,
            )
        )

    summary = build_summary(template, run_rows)
    out = summary_path or DEFAULT_SUMMARY
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    summary["output_path"] = str(out)

    if write_template:
        save_template(template, template_path)

    return summary


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="RQ1 LLM-as-judge referent clarity (OpenAI + Claude)")
    parser.add_argument("--discovery", type=Path, default=None, help="Single discovery markdown path")
    parser.add_argument("--all", action="store_true", help="Judge all template entries with discovery_path")
    parser.add_argument(
        "--judges",
        default="openai,claude",
        help="Comma-separated: openai, claude",
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--no-plain", action="store_true", help="Skip fair-plain L2 comparison")
    args = parser.parse_args(argv)

    if not args.all and not args.discovery:
        parser.error("use --all or --discovery PATH")

    judges_list: list[JudgeProvider] = []
    for part in args.judges.split(","):
        p = part.strip().lower()
        if p in ("openai", "claude"):
            judges_list.append(p)  # type: ignore[arg-type]
    if not judges_list:
        parser.error("--judges must include openai and/or claude")

    summary = run(
        template_path=args.template,
        summary_path=args.out,
        discovery=args.discovery,
        all_discoveries=args.all,
        judges=judges_list,
        include_plain=not args.no_plain,
    )
    print(json.dumps(summary, indent=2))
    print(f"\nwritten: {summary['output_path']}")


if __name__ == "__main__":
    main()
