"""
Plain (unstructured) markdown discovery baseline for RQ1 — Wave 4a.

Generates AML scenario write-ups **without** ADL validators. Uses MiMo/OpenAI via
shared `call_discovery_llm`. With no API keys, emits short stub prose for demo/testing.

Outputs: experiments/outputs/plain_discovery_<slug>.md
Template: updates `plain_discovery_path` on `human_rq1_template.json` rows.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .llm_harness import call_discovery_llm, llm_available, resolve_model
from .mimo_client import mimo_config
from .rq1_batch_discover import (
    OUTPUT_DIR,
    SCENARIO_BLUEPRINTS,
    TEMPLATE_PATH,
    highest_batch_suffix,
    load_template,
    save_template,
    slug_from_adl_id,
)

ROOT = Path(__file__).resolve().parent.parent

PLAINT_SYSTEM_PATH = ROOT / "prompts" / "write_discovery_plain.md"


def next_plain_need_index(template: dict) -> int | None:
    """First row that has ADL discovery but lacks a plain_discovery_path."""
    for i, e in enumerate(template.get("entries", [])):
        if not e.get("adl_id"):
            continue
        if not str(e.get("discovery_path") or "").strip():
            continue
        if str(e.get("plain_discovery_path") or "").strip():
            continue
        return i
    return None


def count_plain_paths(template: dict) -> int:
    return sum(
        1
        for e in template.get("entries", [])
        if e.get("adl_id") and str(e.get("plain_discovery_path") or "").strip()
    )


STUB_BODY: dict[str, str] = {
    "peripheral-trap": (
        '<!-- scenario-slug: peripheral-trap -->\n'
        '# Peripheral Attention Trap (plain baseline)\n\n'
        "**They** route value through corridors **it** ignores while **this** hides behind "
        "**that** benign hub traffic. Operators chase **it**, but missing **them** blinds "
        "the hunt until sinks absorb what **they** never named.\n\n"
        "Alerts pile on flashy nodes yet **those** feeders keep splitting before anyone ties "
        "**this** funnel to beneficiaries **it** only hints at.\n"
    ),
    "smurfing-pattern": (
        '<!-- scenario-slug: smurfing-pattern -->\n'
        '# Smurfing Pattern (plain baseline)\n\n'
        "**It** slips under CTR because **they** fan deposits through **them** overnight. "
        "**This** structuring looks petty until **it** merges—then **those** corridors "
        "reveal whom **they** actually serve.\n\n"
        "Shared fingerprints echo across **them**, but **that** linkage stays fuzzy until "
        "consolidation proves **they** pooled intent.\n"
    ),
    "crypto-mixer": (
        '<!-- scenario-slug: crypto-mixer -->\n'
        '# Crypto Mixer Exposure (plain baseline)\n\n'
        "**They** tumble through mixer hops and **it** peels until **they** cash out via "
        "stablecoins. **This** wallet cluster talks to contracts **those** explorers label, "
        "yet **it** still hides who fronts **them** upstream.\n\n"
        "**That** peeling chain drags fiat spikes while **they** launder plausible deniability "
        "about **that** intermediary everyone suspects.\n"
    ),
}


def plain_task_markdown(slug: str, *, blueprint: dict[str, str] | None = None) -> str:
    bp = blueprint or next(b for b in SCENARIO_BLUEPRINTS if b["slug"] == slug)
    return f"""Scenario assignment ({bp["slug"]}).

{bp["scenario"]}

Write unstructured markdown (~250–450 words unless constraints prevent). Mention concrete monitoring cues from the AML concept reference cited in Wave 4a prompt. FIRST line MUST be HTML comment <!-- scenario-slug: {slug} -->."""


def prose_markdown_body(path: Path) -> str:
    """Full markdown prose for judging (minimal optional YAML strip)."""
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


def plain_output_relative(slug: str, *, batch_suffix: str | None = None) -> str:
    name = (
        f"plain_discovery_{slug}_batch{batch_suffix}.md"
        if batch_suffix
        else f"plain_discovery_{slug}.md"
    )
    return str((ROOT / "experiments" / "outputs" / name).relative_to(ROOT))


def write_stub_to_path(slug: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(STUB_BODY[slug], encoding="utf-8")
    return out_path


def _sync_plain_paths_canonical_three(template: dict) -> None:
    for entry in template.get("entries", []):
        slug = slug_from_adl_id(entry.get("adl_id"))
        if slug:
            entry["plain_discovery_path"] = plain_output_relative(slug)


def extend_plain_paths_rotate(
    *,
    template: dict,
    template_path: Path,
    out_dir: Path,
    target_complete: int,
    model: str | None,
    max_retries: int,
    stub_fallback: bool,
) -> tuple[list[dict], int]:
    """Fill rows missing plain paths with per-row plain_discovery_*.md (batch suffix).

    Rows are iterated in template order (`next_plain_need_index`). Each emission uses
    the row's AML slug from ``disc-llm-*`` identifiers.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    next_bn = highest_batch_suffix(template, out_dir=out_dir) + 1
    results: list[dict] = []

    completed = count_plain_paths(template)

    while completed < target_complete:
        idx = next_plain_need_index(template)
        if idx is None:
            break
        entry = template["entries"][idx]
        slug = slug_from_adl_id(entry.get("adl_id"))
        if not slug:
            break
        batch_suffix = f"{next_bn:03d}"
        next_bn += 1
        out_name = f"plain_discovery_{slug}_batch{batch_suffix}.md"
        summary = generate_one_plain_output(
            slug,
            output_dir=out_dir,
            output_name=out_name,
            model=model,
            max_retries=max_retries,
            stub_fallback=stub_fallback,
        )

        rp = ""
        ok = summary.get("status") in ("completed", "stub_written")
        if summary.get("path"):
            dp = Path(str(summary["path"])).resolve()
            rp = str(dp.relative_to(ROOT)) if dp.is_relative_to(ROOT) else str(dp)

        ent = template["entries"][idx]
        if ok and rp:
            ent["plain_discovery_path"] = rp
            completed = count_plain_paths(template)

        save_template(template, template_path)
        results.append({"slot": idx, **summary})

    final_c = count_plain_paths(template)
    return results, final_c


def generate_one_plain_output(
    slug: str,
    *,
    output_dir: Path,
    output_name: str | None = None,
    model: str | None = None,
    max_retries: int = 1,
    stub_fallback: bool = False,
) -> dict[str, object]:
    """Emit one plain-discovery file; validates presence of slug marker only."""
    out_dir = output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = output_name or f"plain_discovery_{slug}.md"
    out_path = out_dir / fname
    blueprint = next(b for b in SCENARIO_BLUEPRINTS if b["slug"] == slug)
    marker = f"<!-- scenario-slug: {slug} -->"

    if not llm_available():
        if stub_fallback or os.environ.get("RQ1_PLAIN_STUB", "").strip():
            write_stub_to_path(slug, out_path)
            return {"slug": slug, "status": "stub_written", "path": str(out_path), "reason": "no_api_key"}

        return {
            "slug": slug,
            "status": "skipped",
            "path": None,
            "reason": "No LLM API key (set MIMO_API_KEY / OPENAI_API_KEY or run with --stub / RQ1_PLAIN_STUB)",
        }

    system = PLAINT_SYSTEM_PATH.read_text(encoding="utf-8")
    task = plain_task_markdown(slug, blueprint=blueprint)

    last_err = ""
    use_model = resolve_model(model)
    mname = use_model or (mimo_config()[2] if mimo_config() else "gpt-4o-mini")

    for attempt in range(1 + max(0, max_retries)):
        try:
            raw = call_discovery_llm(system, task, model=use_model)
        except Exception as e:
            last_err = str(e)
            continue
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        ok = marker in text
        out_path.write_text(text, encoding="utf-8")

        if ok:
            return {
                "slug": slug,
                "status": "completed",
                "path": str(out_path),
                "model": mname,
                "attempt": attempt + 1,
            }
        last_err = "missing slug marker comment"
        task = (
            plain_task_markdown(slug, blueprint=blueprint)
            + f"\n\nFix: output MUST contain line {marker!r} as the FIRST line verbatim."
        )

    if stub_fallback:
        write_stub_to_path(slug, out_path)
        return {"slug": slug, "status": "stub_written", "path": str(out_path), "reason": last_err}

    return {"slug": slug, "status": "generation_failed", "path": None, "errors": last_err}


def run_canonical_three(
    *,
    model: str | None = None,
    output_dir: Path | None = None,
    template_path: Path | None = None,
    max_retries: int = 1,
    stub_fallback: bool = False,
    update_template: bool = True,
) -> dict:
    """Write three AML plain baselines aligned to rq1_batch_discover slug order."""
    out_dir = output_dir or OUTPUT_DIR
    tp = Path(template_path) if template_path is not None else TEMPLATE_PATH
    summary_rows: list[dict] = []

    for blueprint in SCENARIO_BLUEPRINTS:
        slug = blueprint["slug"]
        row = generate_one_plain_output(
            slug,
            output_dir=out_dir,
            model=model,
            max_retries=max_retries,
            stub_fallback=stub_fallback,
        )
        summary_rows.append(row)

    if update_template:
        tpl = load_template(tp)
        _sync_plain_paths_canonical_three(tpl)
        save_template(tpl, tp)

    ok = sum(1 for r in summary_rows if r.get("status") in ("completed", "stub_written"))
    return {
        "status": "completed" if ok == 3 else "partial",
        "n_written": ok,
        "results": summary_rows,
        "template_path": str(tp),
    }


def run_expand_plain(
    *,
    target_complete: int,
    model: str | None,
    output_dir: Path | None,
    template_path: Path | None,
    max_retries: int,
    stub_fallback: bool,
) -> dict:
    tp = template_path or TEMPLATE_PATH
    tpl = load_template(tp)
    rows, fc = extend_plain_paths_rotate(
        template=tpl,
        template_path=tp,
        out_dir=output_dir or OUTPUT_DIR,
        target_complete=target_complete,
        model=model,
        max_retries=max_retries,
        stub_fallback=stub_fallback,
    )
    return {
        "status": "completed" if fc >= target_complete else "partial",
        "target_complete": target_complete,
        "n_plain_paths": fc,
        "results": rows,
        "template_path": str(tp),
    }


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Plain markdown AML baseline for RQ1")
    parser.add_argument("--model", default=None, help="Override LLM model (OpenAI MiMo-compatible)")
    parser.add_argument("--template", default=str(TEMPLATE_PATH), help="Human eval JSON")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument(
        "--stub",
        action="store_true",
        help="Emit demo stubs when MiMo/OpenAI unavailable (requires no API)",
    )
    parser.add_argument(
        "--stub-when-invalid",
        action="store_true",
        help="If generation fails slug marker validation, emit stub prose",
    )
    parser.add_argument(
        "--no-update-template",
        action="store_true",
        help="Do not write plain_discovery_path into template rows",
    )
    parser.add_argument(
        "--target-complete",
        type=int,
        default=None,
        help="Fill successive empty template slots (rotating AML topics) until N rows have plain paths",
    )
    args = parser.parse_args(argv)
    tpl_path = Path(args.template)

    sf = args.stub or args.stub_when_invalid or bool(os.environ.get("RQ1_PLAIN_STUB", "").strip())

    if args.target_complete is not None:
        summary = run_expand_plain(
            target_complete=args.target_complete,
            model=args.model,
            output_dir=Path(args.output_dir),
            template_path=tpl_path,
            max_retries=args.max_retries,
            stub_fallback=sf,
        )
    else:
        summary = run_canonical_three(
            model=args.model,
            output_dir=Path(args.output_dir),
            template_path=tpl_path,
            max_retries=args.max_retries,
            stub_fallback=sf,
            update_template=not args.no_update_template,
        )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
