"""
RQ1 LLM-as-judge referent clarity — ADL vs fair-plain strip vs unstructured plain baseline.

Judge providers default to Cursor-proxy labels (**openai_proxy**, **composer_proxy**). Direct API routing
(OpenAI vs Anthropic) is only enabled when caller keys are configured; alternatively pass ``chat_fn`` for
sandbox or Cursor-mediated scoring.

Scores L2 prose for structured ADL parses, fair-plain stripping of fenced blocks only, plus full Markdown
written by ``experiments/rq1_plain_discover.py`` comparisons.

Examples:
  python -m experiments.rq1_llm_judge --summarize-from-template --plain-fixture experiments/fixtures/plain_llm_judge_scores_demo.json
  python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only                 # merges data/eval/rq1_plain_llm_live_proxy_wave6b.json
  python -m experiments.rq1_llm_judge --summarize-from-template --plain-live-scores PATH.json
  python -m experiments.rq1_llm_judge --discovery experiments/outputs/llm_discovery_peripheral-trap.md
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast

from adl_lite import parse_file
from experiments.judge_clients import chat_claude, chat_openai, parse_judge_response
from experiments.rq1_batch_discover import slug_from_adl_id
from experiments.rq1_plain_discover import prose_markdown_body

from .baselines.fair_plain import adl_to_fair_plain

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "data" / "eval" / "human_rq1_template.json"
DEFAULT_SUMMARY = ROOT / "docs" / "experiments" / "rq1_llm_judge_summary.json"
DEFAULT_PLAIN_LLM_FIXTURE = ROOT / "experiments" / "fixtures" / "plain_llm_judge_scores_demo.json"
DEFAULT_PLAIN_LLM_LIVE_PROXY = ROOT / "data" / "eval" / "rq1_plain_llm_live_proxy_wave6b.json"
JUDGE_PROMPT_PATH = ROOT / "prompts" / "judge_referent_clarity.md"

_MODEL_OPENAI_PROXY = "gpt-5.3-codex (cursor-proxy)"
_MODEL_COMPOSER_PROXY = "composer-2-fast (cursor-proxy)"

FIELD_OPENAI = "llm_judge_openai"
FIELD_COMPOSER = "llm_judge_composer"
FIELD_OPENAI_PLAIN = "llm_judge_openai_plain"
FIELD_COMPOSER_PLAIN = "llm_judge_composer_plain"
FIELD_OPENAI_PLLM = "llm_judge_openai_plain_llm"
FIELD_COMPOSER_PLLM = "llm_judge_composer_plain_llm"

ProxyJudgeProvider = Literal["openai_proxy", "composer_proxy"]
DISAGREEMENT_THRESHOLD = 2

JudgeChatFn = Callable[[ProxyJudgeProvider, str, str], str]


def load_template(path: Path | None = None) -> dict:
    return json.loads((path or DEFAULT_TEMPLATE).read_text(encoding="utf-8"))


def save_template(template: dict, path: Path | None = None) -> None:
    (path or DEFAULT_TEMPLATE).write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")


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


def text_for_plain_discovery(path: Path) -> str:
    return prose_markdown_body(path.resolve())


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _score_from_nested(obj: object) -> float | None:
    if isinstance(obj, dict):
        raw = obj.get("score")
        if raw is not None:
            return float(raw)
    return None


def default_proxy_chat(proxy: ProxyJudgeProvider, system: str, user: str) -> str:
    """Route proxy labels onto OpenAI/Anthropic clients (composer misuses Claude API for parity tests)."""
    if proxy == "openai_proxy":
        return chat_openai(system, user)
    if proxy == "composer_proxy":
        return chat_claude(system, user)
    raise ValueError(f"unknown judge proxy label: {proxy}")


def judge_text(
    l2_text: str,
    *,
    proxy: ProxyJudgeProvider,
    system_prompt: str | None = None,
    chat_fn: JudgeChatFn | None = None,
) -> dict[str, Any]:
    system = system_prompt or load_judge_prompt()
    raw = chat_fn(proxy, system, l2_text) if chat_fn else default_proxy_chat(proxy, system, l2_text)
    parsed = parse_judge_response(raw)
    label_tag = {"openai_proxy": "gpt-5.3-codex", "composer_proxy": "composer-2-fast"}[proxy]
    model_name = (
        f"{label_tag} (cursor-proxy)"
        if chat_fn is None
        else f"{label_tag} (inject-chat-fn)"
    )
    return {
        "score": parsed["referent_clarity"],
        "model": model_name,
        "rationale": parsed["rationale"],
    }


def plain_llm_fixture_path(fixture: Path | None) -> Path:
    return fixture or DEFAULT_PLAIN_LLM_FIXTURE


def _unpack_proxy_score(bundle: dict[str, Any] | int | float | None, *, rationale_hint: str) -> tuple[int, str]:
    """Return integral score plus rationale pulled from ints or richer dict payloads."""
    if bundle is None:
        raise ValueError("missing proxied judge score")
    if isinstance(bundle, dict):
        scr = bundle.get("score")
        rationale = str(bundle.get("rationale") or "").strip()
        if scr is None:
            raise ValueError("score dict missing score field")
        if not rationale:
            rationale = rationale_hint
        return int(scr), rationale
    return int(bundle), rationale_hint


def merge_plain_llm_live_scores(
    template: dict,
    scores_json: Path,
    *,
    note: str = "Live Cursor proxy scores merged from JSON artifact",
) -> dict[str, Any]:
    """Hydrate unstructured plain-baseline judgments without invoking external APIs."""
    data = json.loads(scores_json.read_text(encoding="utf-8"))
    per_slug = data.get("per_slug", data)
    if not isinstance(per_slug, dict):
        raise ValueError("scores JSON must expose per_slug mapping")

    models = {"openai_proxy": _MODEL_OPENAI_PROXY, "composer_proxy": _MODEL_COMPOSER_PROXY}

    updated = 0
    for entry in template.get("entries", []):
        slug = slug_from_adl_id(entry.get("adl_id"))
        if slug is None or not str(entry.get("discovery_path") or "").strip():
            continue
        slug_bundle = per_slug.get(slug)
        if slug_bundle is None or not isinstance(slug_bundle, dict):
            raise KeyError(f"scores JSON missing slug payload for {slug}")

        ao_bundle = slug_bundle.get("openai_proxy")
        bc_bundle = slug_bundle.get("composer_proxy")

        ao, ao_rationale = _unpack_proxy_score(
            cast(dict[str, Any] | int | float | None, ao_bundle),
            rationale_hint=f"{note} slug={slug} judge=A",
        )
        bc, bc_rationale = _unpack_proxy_score(
            cast(dict[str, Any] | int | float | None, bc_bundle),
            rationale_hint=f"{note} slug={slug} judge=B",
        )

        entry[FIELD_OPENAI_PLLM] = {"score": int(ao), "model": models["openai_proxy"], "rationale": ao_rationale}
        entry[FIELD_COMPOSER_PLLM] = {"score": int(bc), "model": models["composer_proxy"], "rationale": bc_rationale}
        entry["referent_clarity_openai_plain_llm"] = int(ao)
        entry["referent_clarity_composer_plain_llm"] = int(bc)
        updated += 1

    return {"n_updated": updated, "note": note, "source": str(scores_json)}


def merge_plain_llm_fixture(
    template: dict,
    fixture_json: Path,
    *,
    note: str = "Fixture merge (offline demo adjudication)",
) -> dict[str, Any]:
    data = json.loads(fixture_json.read_text(encoding="utf-8"))
    per_slug = data.get("per_slug", data)
    if not isinstance(per_slug, dict):
        raise ValueError("fixture must expose per_slug object")

    models = {
        "openai_proxy": "gpt-5.3-codex (fixture)",
        "composer_proxy": "composer-2-fast (fixture)",
    }
    rationales = (
        "[Fixture] Compressed pronoun-heavy baseline vs anchored ADL L2 prose. "
        f"{fixture_json.relative_to(ROOT)!s}"
        if fixture_json.is_relative_to(ROOT)
        else fixture_json.as_posix()
    )

    updated = 0
    for entry in template.get("entries", []):
        slug = slug_from_adl_id(entry.get("adl_id"))
        if slug is None or not str(entry.get("discovery_path") or "").strip():
            continue
        slug_scores = per_slug.get(slug)
        if slug_scores is None or not isinstance(slug_scores, dict):
            raise KeyError(f"fixture missing slug {slug}")

        ao = slug_scores["openai_proxy"]
        bc = slug_scores["composer_proxy"]
        entry[FIELD_OPENAI_PLLM] = {
            "score": int(ao),
            "model": models["openai_proxy"],
            "rationale": rationales + f" slug={slug} judge=openai_proxy",
        }
        entry[FIELD_COMPOSER_PLLM] = {
            "score": int(bc),
            "model": models["composer_proxy"],
            "rationale": rationales + f" slug={slug} judge=composer_proxy",
        }
        entry["referent_clarity_openai_plain_llm"] = int(ao)
        entry["referent_clarity_composer_plain_llm"] = int(bc)
        updated += 1

    return {"n_updated": updated, "note": note}


def entries_with_discovery(template: dict) -> list[dict]:
    return [e for e in template.get("entries", []) if str(e.get("discovery_path") or "").strip()]


def _plain_llm_uri(entry: dict) -> Path | None:
    rel = (entry.get("plain_discovery_path") or "").strip()
    if not rel:
        slug = slug_from_adl_id(entry.get("adl_id"))
        if not slug:
            return None
        rel = str((ROOT / "experiments" / "outputs" / f"plain_discovery_{slug}.md").relative_to(ROOT))
        entry["plain_discovery_path"] = rel
    cand = _resolve_path(rel)
    return cand


def run_judges_for_entry(
    entry: dict,
    proxies: list[ProxyJudgeProvider],
    *,
    include_fair_plain: bool,
    include_plain_llm_live: bool,
    system_prompt: str | None = None,
    chat_fn: JudgeChatFn | None = None,
) -> dict[str, Any]:
    dp = entry.get("discovery_path")
    if not dp:
        raise ValueError("missing discovery_path")
    path = _resolve_path(cast(str, dp))
    if not path.exists():
        raise FileNotFoundError(path)

    out: dict[str, Any] = {
        "adl_id": entry.get("adl_id"),
        "discovery_path": entry.get("discovery_path"),
        "plain_discovery_path": entry.get("plain_discovery_path"),
        "judges": {p: {} for p in proxies},
        "skipped": [],
        "pll_judge_disagreement": False,
    }

    adl_txt = l2_body_from_path(path, plain=False)
    fair_plain = l2_body_from_path(path, plain=True) if include_fair_plain else None

    plain_path = None
    plain_txt = ""
    if include_plain_llm_live:
        plain_path_attempt = _plain_llm_uri(entry)
        if plain_path_attempt and plain_path_attempt.exists():
            plain_path = plain_path_attempt
            plain_txt = text_for_plain_discovery(plain_path)
        elif plain_path_attempt:
            # Allow judge run to skip pll when file absent (artifacts gitignored upstream)
            plain_txt = ""

    for px in proxies:
        try:
            adl_pack = judge_text(adl_txt, proxy=px, system_prompt=system_prompt, chat_fn=chat_fn)
            entry[field_for_proxy_adl(px)] = adl_pack
            entry[field_for_proxy_referent(px)] = adl_pack["score"]
            out["judges"][px]["adl"] = adl_pack
        except Exception as e:
            out["skipped"].append({"provider": px, "mode": "adl", "reason": str(e)})

        if include_fair_plain and fair_plain is not None:
            try:
                pl = judge_text(fair_plain, proxy=px, system_prompt=system_prompt, chat_fn=chat_fn)
                entry[field_for_proxy_plain(px)] = pl
                out["judges"][px]["plain"] = pl
            except Exception as e:
                out["judges"][px]["plain_error"] = str(e)

        if include_plain_llm_live and plain_txt.strip():
            try:
                pll = judge_text(plain_txt, proxy=px, system_prompt=system_prompt, chat_fn=chat_fn)
                entry[field_for_proxy_plain_llm(px)] = pll
                entry[field_for_plain_llm_referent(px)] = pll["score"]
                out["judges"][px]["plain_llm"] = pll
            except Exception as e:
                out["judges"][px]["plain_llm_error"] = str(e)

    oa_adl = _score_from_nested(entry.get(FIELD_OPENAI))
    cm_adl = _score_from_nested(entry.get(FIELD_COMPOSER))
    if oa_adl is not None and cm_adl is not None:
        out["abs_diff_a_b"] = abs(int(oa_adl) - int(cm_adl))
        out["judge_disagreement"] = out["abs_diff_a_b"] >= DISAGREEMENT_THRESHOLD
    pll_a = _score_from_nested(entry.get(FIELD_OPENAI_PLLM))
    pll_b = _score_from_nested(entry.get(FIELD_COMPOSER_PLLM))
    if pll_a is not None and pll_b is not None:
        out["pll_judge_disagreement"] = abs(int(pll_a) - int(pll_b)) >= DISAGREEMENT_THRESHOLD

    return out


def field_for_proxy_adl(proxy: ProxyJudgeProvider) -> str:
    return FIELD_OPENAI if proxy == "openai_proxy" else FIELD_COMPOSER


def field_for_proxy_plain(proxy: ProxyJudgeProvider) -> str:
    return FIELD_OPENAI_PLAIN if proxy == "openai_proxy" else FIELD_COMPOSER_PLAIN


def field_for_proxy_plain_llm(proxy: ProxyJudgeProvider) -> str:
    return FIELD_OPENAI_PLLM if proxy == "openai_proxy" else FIELD_COMPOSER_PLLM


def field_for_proxy_referent(proxy: ProxyJudgeProvider) -> str:
    return "referent_clarity_openai_proxy" if proxy == "openai_proxy" else "referent_clarity_composer_proxy"


def field_for_plain_llm_referent(proxy: ProxyJudgeProvider) -> str:
    return (
        "referent_clarity_openai_plain_llm"
        if proxy == "openai_proxy"
        else "referent_clarity_composer_plain_llm"
    )


def summarize_from_template(
    template: dict,
    *,
    run_rows: list[dict] | None = None,
) -> dict[str, Any]:
    """Build ``rq1_llm_judge_summary.json`` aggregates from hydrated template rows."""
    entries_covered = entries_with_discovery(template)

    proxies: tuple[ProxyJudgeProvider, ProxyJudgeProvider] = ("openai_proxy", "composer_proxy")
    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metric": "llm_referent_clarity",
        "label": "LLM-as-judge (Cursor proxy, no user API keys)",
        "n_discoveries": len(entries_covered),
        "disagreement_threshold": DISAGREEMENT_THRESHOLD,
        "judge_setup": {
            "judge_a": "gpt-5.3-codex (cursor-proxy) strict",
            "judge_b": "composer-2-fast (cursor-proxy) careful",
            "claude_status": "skipped_unavailable_region",
        },
        "per_judge": {},
        "fair_plain_comparison": {},
        "plain_llm": {
            "label": "ADL Markdown L2 vs MiMo unstructured plain baseline (live adjudication artifact or bundled fixture fallback)",
            "per_judge": {},
            "plain_llm_judge_disagreement_count": 0,
        },
        "entries": [],
    }

    if run_rows:
        summary["entries"] = run_rows
    else:
        for ent in entries_covered:
            row = _template_entry_to_summary_row(ent, proxies)
            summary["entries"].append(row)

    per_judge_adl_avg: list[float] = []

    for px in proxies:
        f_adl = field_for_proxy_adl(px)
        f_pl = field_for_proxy_plain(px)
        f_pll = field_for_proxy_plain_llm(px)
        adl_scores: list[float] = []
        plain_scores: list[float] = []
        pll_scores: list[float] = []
        delta_fp: list[float] = []
        delta_pll: list[float] = []
        model_hint = None
        pll_model_hint = None

        for ent in entries_covered:
            ao = ent.get(f_adl)
            s_adl = _score_from_nested(ao)
            if s_adl is not None:
                adl_scores.append(s_adl)
                if isinstance(ao, dict):
                    model_hint = ao.get("model") or model_hint
            s_pl = _score_from_nested(ent.get(f_pl))
            if s_adl is not None and s_pl is not None:
                plain_scores.append(s_pl)
                delta_fp.append(s_adl - s_pl)
            s_pll = _score_from_nested(ent.get(f_pll))
            if s_adl is not None and s_pll is not None:
                pll_scores.append(s_pll)
                delta_pll.append(s_adl - s_pll)
                po = ent.get(f_pll)
                if isinstance(po, dict):
                    pll_model_hint = po.get("model") or pll_model_hint

        pj: dict[str, Any] = {
            "model": model_hint,
            "n_scored": len(adl_scores),
            "mean_adl": _mean(adl_scores),
        }
        if plain_scores:
            pj["mean_plain"] = _mean(plain_scores)
            pj["mean_delta_adl_minus_plain"] = _mean(delta_fp)
        summary["per_judge"][px] = pj

        pll_block: dict[str, Any] = {
            "model": pll_model_hint,
            "n_scored": len(pll_scores),
            "mean_plain_llm": _mean(pll_scores),
            "mean_delta_adl_minus_plain_llm": _mean(delta_pll),
        }
        summary["plain_llm"]["per_judge"][px] = pll_block
        if pj.get("mean_adl") is not None:
            per_judge_adl_avg.append(float(pj["mean_adl"]))  # type: ignore[arg-type]

    summary["fair_plain_comparison"] = {
        "judges_scored": list(proxies),
        "mean_across_judges_adl": _mean(per_judge_adl_avg),
        "adl_vs_plain_delta_mean": {
            px: float(summary["per_judge"][px]["mean_delta_adl_minus_plain"] or 0.0)
            for px in proxies
            if summary["per_judge"][px].get("mean_delta_adl_minus_plain") is not None
        },
    }

    disagreement_count_fp = sum(1 for sr in summary["entries"] if sr.get("judge_disagreement"))
    pll_disagreements = sum(1 for sr in summary["entries"] if sr.get("pll_judge_disagreement"))
    summary["plain_llm"]["plain_llm_judge_disagreement_count"] = pll_disagreements

    plain_llm_pool: list[float] = []
    delta_pll_pool: list[float] = []
    for px in proxies:
        block = summary["plain_llm"]["per_judge"][px]
        mpl = block.get("mean_plain_llm")
        if mpl is not None:
            plain_llm_pool.append(float(mpl))
        md = block.get("mean_delta_adl_minus_plain_llm")
        if md is not None:
            delta_pll_pool.append(float(md))

    summary["plain_llm"]["mean_across_judges_plain_llm"] = _mean(plain_llm_pool)
    summary["plain_llm"]["mean_delta_adl_minus_plain_llm_between_judges_mean"] = _mean(delta_pll_pool)

    legacy_fp_delta = summary["fair_plain_comparison"].get("adl_vs_plain_delta_mean", {})
    summary["judges_scored"] = list(proxies)
    summary["mean_across_judges_adl"] = summary["fair_plain_comparison"]["mean_across_judges_adl"]
    summary["disagreement_count"] = disagreement_count_fp
    summary["adl_vs_plain_delta_mean"] = legacy_fp_delta if isinstance(legacy_fp_delta, dict) else {}
    summary["adl_vs_plain_plain_llm_delta_mean"] = {
        px: float(summary["plain_llm"]["per_judge"][px].get("mean_delta_adl_minus_plain_llm") or 0.0)
        for px in proxies
        if summary["plain_llm"]["per_judge"][px].get("mean_delta_adl_minus_plain_llm") is not None
    }

    summary["judges_skipped_note"] = "Claude direct API deliberately unused; Composer proxy substitutes via Anthropic-compatible tests."

    return summary


def _template_entry_to_summary_row(ent: dict, proxies: tuple[ProxyJudgeProvider, ...]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "adl_id": ent.get("adl_id"),
        "discovery_path": ent.get("discovery_path"),
        "plain_discovery_path": ent.get("plain_discovery_path"),
        "judges": {p: {} for p in proxies},
    }

    for px in proxies:
        sub: dict[str, Any] = {}
        ad_key = field_for_proxy_adl(px)
        fp_key = field_for_proxy_plain(px)
        pll_key = field_for_proxy_plain_llm(px)
        ad = ent.get(ad_key)
        if isinstance(ad, dict):
            sub["adl"] = ad
        pl = ent.get(fp_key)
        if isinstance(pl, dict):
            sub["plain"] = pl
        pll = ent.get(pll_key)
        if isinstance(pll, dict):
            sub["plain_llm"] = pll
        row["judges"][px] = sub

    oa_adl = _score_from_nested(ent.get(FIELD_OPENAI))
    cm_adl = _score_from_nested(ent.get(FIELD_COMPOSER))
    if oa_adl is not None and cm_adl is not None:
        row["abs_diff_a_b"] = abs(int(oa_adl) - int(cm_adl))
        row["judge_disagreement"] = row["abs_diff_a_b"] >= DISAGREEMENT_THRESHOLD
    else:
        row["abs_diff_a_b"] = None
        row["judge_disagreement"] = None

    pll_a = _score_from_nested(ent.get(FIELD_OPENAI_PLLM))
    pll_b = _score_from_nested(ent.get(FIELD_COMPOSER_PLLM))
    row["pll_judge_disagreement"] = (
        abs(int(pll_a) - int(pll_b)) >= DISAGREEMENT_THRESHOLD
        if pll_a is not None and pll_b is not None
        else None
    )
    return row


def build_summary(template: dict, run_rows: list[dict]) -> dict[str, Any]:
    """Legacy alias retained for experiments/test_rq1_llm_judge.py."""
    return summarize_from_template(template, run_rows=run_rows)


def run(
    *,
    template_path: Path | None = None,
    summary_path: Path | None = None,
    discovery: Path | None = None,
    all_discoveries: bool = False,
    proxies: list[ProxyJudgeProvider] | None = None,
    include_fair_plain: bool = True,
    include_plain_llm_live: bool = False,
    summarize_only: bool = False,
    merge_plain_fixture_auto: bool = True,
    plain_fixture: Path | None = None,
    plain_live_scores: Path | None = None,
    proxy_only: bool = False,
    write_template: bool = True,
    system_prompt: str | None = None,
    chat_fn: JudgeChatFn | None = None,
) -> dict[str, Any]:
    template = load_template(template_path)

    merged_note: dict[str, Any] | None = None
    if summarize_only:
        merge_performed = False

        liv_path = Path(plain_live_scores).expanduser().resolve() if plain_live_scores is not None else None
        if liv_path is not None:
            if not liv_path.exists():
                raise FileNotFoundError(liv_path)
            merged_note = merge_plain_llm_live_scores(template, liv_path)
            merge_performed = True
        elif proxy_only:
            score_path = DEFAULT_PLAIN_LLM_LIVE_PROXY
            if not score_path.exists():
                raise FileNotFoundError(score_path)
            merged_note = merge_plain_llm_live_scores(template, score_path)
            merge_performed = True
        elif plain_fixture is not None:
            cand = plain_llm_fixture_path(plain_fixture)
            merged_note = merge_plain_llm_fixture(template, cand)
            merge_performed = True
        elif merge_plain_fixture_auto:
            fx = plain_llm_fixture_path(None)
            if fx.exists():
                merged_note = merge_plain_llm_fixture(template, fx)
                merge_performed = True

        if write_template and merge_performed:
            save_template(template, template_path)

    elif plain_fixture:
        merged_note = merge_plain_llm_fixture(template, plain_llm_fixture_path(plain_fixture))
        if write_template:
            save_template(template, template_path)

    plist = proxies or ["openai_proxy", "composer_proxy"]

    targets = entries_with_discovery(template)
    if discovery:
        rel = str(discovery.relative_to(ROOT)) if discovery.is_relative_to(ROOT) else str(discovery)
        filt = []
        for e in targets:
            ep = cast(str, e["discovery_path"])
            if ep == rel or _resolve_path(ep) == discovery:
                filt.append(e)
        targets = filt
        if not targets:
            targets = [{"discovery_path": rel, "adl_id": None}]

    run_rows: list[dict] = []
    if not summarize_only:
        if not all_discoveries and not discovery:
            raise ValueError("specify discovery path or --all or --summarize-from-template")

        for entry in targets:
            dp = entry.get("discovery_path")
            if not dp:
                continue
            if not _resolve_path(cast(str, dp)).exists():
                # LLM discovery artifacts under experiments/outputs/ are often gitignored
                continue
            run_rows.append(
                run_judges_for_entry(
                    entry,
                    plist,
                    include_fair_plain=include_fair_plain,
                    include_plain_llm_live=include_plain_llm_live,
                    system_prompt=system_prompt,
                    chat_fn=chat_fn,
                )
            )
        if write_template:
            save_template(template, template_path)

    summary = summarize_from_template(template, run_rows=run_rows if run_rows else None)
    skipped_set = []
    for rr in run_rows:
        skipped_set.extend(s.get("provider", "?") for s in (rr.get("skipped") or []))
    summary["judges_skipped"] = sorted(set(skipped_set))
    summary["plain_llm_fixture_merge_note"] = merged_note
    out = summary_path or DEFAULT_SUMMARY
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    summary["output_path"] = str(out)
    return summary


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="RQ1 LLM-as-judge referent clarity (proxy labels)")
    parser.add_argument("--discovery", type=Path, default=None)
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--summarize-from-template",
        action="store_true",
        help="Rebuild summary JSON; merges plain prose scores (fixture by default)",
    )
    parser.add_argument("--plain-fixture", type=Path, default=None, help="Alternate plain-LLM score fixture")
    parser.add_argument("--no-plain-fixture", action="store_true")
    parser.add_argument(
        "--proxy-only",
        action="store_true",
        help="Prefer live Cursor-proxy JSON (default data/eval/rq1_plain_llm_live_proxy_wave6b.json) during summarize-only",
    )
    parser.add_argument(
        "--plain-live-scores",
        type=Path,
        default=None,
        help="Explicit plain-LLM adjudication artifact (structured like data/eval/rq1_plain_llm_live_proxy_wave6b.json)",
    )
    parser.add_argument(
        "--plain-llm-live",
        action="store_true",
        help="Judge plain_discovery_path prose during live runs (--all/--discovery)",
    )
    parser.add_argument("--judges", default="openai_proxy,composer_proxy")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--no-fair-plain", action="store_true")
    parser.add_argument("--no-write-template", action="store_true")
    args = parser.parse_args(argv)

    plist: list[ProxyJudgeProvider] = []
    for part in args.judges.split(","):
        p = part.strip().lower()
        if p in ("openai_proxy", "openai"):
            plist.append("openai_proxy")
        elif p in ("composer_proxy", "composer"):
            plist.append("composer_proxy")
        elif p == "claude":
            plist.append("composer_proxy")

    summary = run(
        template_path=args.template,
        summary_path=args.out,
        discovery=args.discovery,
        all_discoveries=args.all,
        proxies=plist or ["openai_proxy", "composer_proxy"],
        include_fair_plain=not args.no_fair_plain,
        include_plain_llm_live=args.plain_llm_live,
        summarize_only=args.summarize_from_template,
        merge_plain_fixture_auto=not args.no_plain_fixture,
        plain_fixture=args.plain_fixture,
        plain_live_scores=args.plain_live_scores,
        proxy_only=args.proxy_only,
        write_template=not args.no_write_template,
    )
    print(json.dumps(summary, indent=2))
    print(f"\nwritten: {summary['output_path']}")


if __name__ == "__main__":
    main()
