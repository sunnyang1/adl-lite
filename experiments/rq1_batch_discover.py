"""
Optional batch LLM discovery runner for RQ1 human eval (AML scenarios).

Requires MIMO_API_KEY or OPENAI_API_KEY. Skips gracefully when no key is set.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .llm_harness import llm_available, run_llm_sim, write_llm_log

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "data" / "eval" / "human_rq1_template.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

SCENARIO_BLUEPRINTS: list[dict[str, str]] = [
    {
        "slug": "peripheral-trap",
        "scenario": (
            "Peripheral Attention Trap — graph peripheral node concentration while value consolidates toward a "
            "hidden sink; align with aml-attention-trap monitoring signals"
        ),
        "task": """\
Task: Write an ADL Lite discovery document about "Peripheral Attention Trap" in AML.
Output RAW markdown only — do NOT wrap the document in a ```markdown code fence.

Requirements:
- YAML front matter: adl_type: discovery, adl_id: {adl_id}, domain: financial_aml,
  scope: private/ceiec-aml, status: provisional
- No pronouns: this, that, it, 这个, 那个
- At least one ```adl:relation block and one ```adl:evidence block
- evidence_type must be one of: vector_cluster, simulator_run, human_expert, cross_reference, empirical_observation
- Align monitoring signals with data/aml/concepts/aml-attention-trap.md (graph peripheral nodes, sink convergence)
""",
    },
    {
        "slug": "smurfing-pattern",
        "scenario": (
            "Smurfing Pattern — sub-threshold deposit structuring across a beneficial-owner network; align with "
            "aml-smurfing CTR threshold heuristics"
        ),
        "task": """\
Task: Write an ADL Lite discovery document about "Smurfing Pattern" in AML.
Output RAW markdown only — do NOT wrap the document in a ```markdown code fence.

Requirements:
- YAML front matter: adl_type: discovery, adl_id: {adl_id}, domain: financial_aml,
  scope: private/ceiec-aml, status: provisional
- No pronouns: this, that, it, 这个, 那个
- At least one ```adl:relation block and one ```adl:evidence block
- evidence_type must be one of: vector_cluster, simulator_run, human_expert, cross_reference, empirical_observation
- Align monitoring signals with data/aml/concepts/aml-smurfing.md (sub-threshold deposits, consolidation transfer)
""",
    },
    {
        "slug": "crypto-mixer",
        "scenario": (
            "Crypto Mixer Exposure — wallet activity linked to tumbler contracts with peel-chain off-ramp patterns; "
            "align with aml-crypto-mix monitoring signals"
        ),
        "task": """\
Task: Write an ADL Lite discovery document about "Crypto Mixer Exposure" in AML.
Output RAW markdown only — do NOT wrap the document in a ```markdown code fence.

Requirements:
- YAML front matter: adl_type: discovery, adl_id: {adl_id}, domain: financial_aml,
  scope: private/ceiec-aml, status: provisional
- No pronouns: this, that, it, 这个, 那个
- At least one ```adl:relation block and one ```adl:evidence block
- evidence_type must be one of: vector_cluster, simulator_run, human_expert, cross_reference, empirical_observation
- Align monitoring signals with data/aml/concepts/aml-crypto-mix.md (mixer contracts, peel-chain off-ramp)
""",
    },
]

# Canonical IDs (backward compatibility + tests.test_batch_scenarios_match_template).
CANON_SCENARIO_SLUGS = ("peripheral-trap", "smurfing-pattern", "crypto-mixer")


def slug_from_adl_id(adl_id: str | None) -> str | None:
    """Resolve AML scenario slug from `disc-llm-*` YAML id (including batch suffix)."""
    if not isinstance(adl_id, str):
        return None
    if not adl_id.startswith("disc-llm-"):
        return None
    tail = adl_id.removeprefix("disc-llm-")
    tail = re.sub(r"-batch\d+$", "", tail)
    if tail not in CANON_SCENARIO_SLUGS:
        return None
    return tail


SCENARIOS = [
    {
        "adl_id": "disc-llm-peripheral-trap",
        "slug": SCENARIO_BLUEPRINTS[0]["slug"],
        "task": SCENARIO_BLUEPRINTS[0]["task"].format(adl_id="disc-llm-peripheral-trap"),
    },
    {
        "adl_id": "disc-llm-smurfing-pattern",
        "slug": SCENARIO_BLUEPRINTS[1]["slug"],
        "task": SCENARIO_BLUEPRINTS[1]["task"].format(adl_id="disc-llm-smurfing-pattern"),
    },
    {
        "adl_id": "disc-llm-crypto-mixer",
        "slug": SCENARIO_BLUEPRINTS[2]["slug"],
        "task": SCENARIO_BLUEPRINTS[2]["task"].format(adl_id="disc-llm-crypto-mixer"),
    },
]


def blueprint_for_slug(slug: str) -> dict[str, str]:
    for bp in SCENARIO_BLUEPRINTS:
        if bp["slug"] == slug:
            return bp
    raise KeyError(slug)


def next_batch_adl_id_yaml_slug(slug: str, batch_suffix: str) -> str:
    """YAML adl_id using hyphens only (YAML field uses same slug style as originals)."""
    root = slug  # peripheral-trap, smurfing-pattern, crypto-mixer
    return f"disc-llm-{root}-batch{batch_suffix}"


def highest_batch_suffix(template: dict, *, out_dir: Path | None = None) -> int:
    hi = 0
    suffix_re = re.compile(r"-batch(\d{3})$")
    for entry in template.get("entries", []):
        aid = entry.get("adl_id")
        if not isinstance(aid, str):
            continue
        m = suffix_re.search(aid)
        if m:
            hi = max(hi, int(m.group(1)))
    # Also scan filenames in output dir for llm_discovery_*_batchNNN pattern
    scan = out_dir or OUTPUT_DIR
    if scan.exists():
        fn_re = re.compile(r"_batch(\d{3})\.md$")
        for p in scan.glob("*.md"):
            m = fn_re.search(p.name)
            if m:
                hi = max(hi, int(m.group(1)))
    return hi


def load_template(path: Path | None = None) -> dict:
    p = path or TEMPLATE_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def save_template(template: dict, path: Path | None = None) -> Path:
    p = path or TEMPLATE_PATH
    p.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    return p


def count_completed(template: dict) -> int:
    n = 0
    for entry in template.get("entries", []):
        if (
            entry.get("validator_pass") is True
            and str(entry.get("discovery_path") or "").strip()
            and entry.get("adl_id")
        ):
            n += 1
    return n


def next_fill_index(template: dict) -> int | None:
    for i, entry in enumerate(template.get("entries", [])):
        if not str(entry.get("discovery_path") or "").strip():
            return i
    return None


def _entry_skeleton(
    *,
    adl_id: str,
    scenario: str,
    discovery_path_rel: str,
    validator_pass: bool,
    notes: str,
) -> dict:
    return {
        "adl_id": adl_id,
        "discovery_path": discovery_path_rel,
        "scenario": scenario,
        "referent_clarity": None,
        "validator_pass": validator_pass,
        "rater": None,
        "notes": notes,
        "llm_judge_openai": None,
        "llm_judge_composer": None,
        "llm_judge_openai_plain": None,
        "llm_judge_composer_plain": None,
        "referent_clarity_openai_proxy": None,
        "referent_clarity_composer_proxy": None,
        "plain_discovery_path": "",
        "referent_clarity_openai_plain_llm": None,
        "referent_clarity_composer_plain_llm": None,
        "llm_judge_openai_plain_llm": None,
        "llm_judge_composer_plain_llm": None,
    }


def apply_entry_at(template: dict, index: int, data: dict) -> None:
    template["entries"][index] = data


def _update_template_entry(template: dict, adl_id: str, discovery_path: Path, validator_pass: bool) -> None:
    rel = discovery_path.relative_to(ROOT) if discovery_path.is_relative_to(ROOT) else discovery_path
    for entry in template.get("entries", []):
        if entry.get("adl_id") == adl_id:
            entry["discovery_path"] = str(rel)
            entry["validator_pass"] = validator_pass
            return


def run_batch(
    *,
    model: str | None = None,
    output_dir: Path | None = None,
    template_path: Path | None = None,
    max_retries: int = 1,
) -> dict:
    """Run LLM discovery for each scenario; update template with paths."""
    if not llm_available():
        return {
            "status": "skipped",
            "reason": "No LLM API key",
            "hint": "export MIMO_API_KEY=tp-... or OPENAI_API_KEY=sk-...",
        }

    out_dir = output_dir or OUTPUT_DIR
    template = load_template(template_path)
    results: list[dict] = []

    for scenario in SCENARIOS:
        result = run_llm_sim(
            model=model,
            output_dir=out_dir,
            max_retries=max_retries,
            discovery_task=scenario["task"],
            expected_adl_id=scenario["adl_id"],
            output_name=f"llm_discovery_{scenario['slug']}.md",
        )
        if result.discovery_path:
            _update_template_entry(
                template,
                scenario["adl_id"],
                result.discovery_path,
                validator_pass=result.status == "completed",
            )
        results.append(
            {
                "adl_id": scenario["adl_id"],
                **result.to_dict(),
            }
        )
        if result.events:
            write_llm_log(result, path=out_dir / f"llm_run_{scenario['slug']}.jsonl")

    save_template(template, template_path)
    completed = sum(1 for r in results if r.get("status") == "completed")
    return {
        "status": "completed" if completed == len(SCENARIOS) else "partial",
        "n_scenarios": len(SCENARIOS),
        "n_completed": completed,
        "results": results,
        "template_path": str(template_path or TEMPLATE_PATH),
    }


def run_batch_expand(
    *,
    target_complete: int,
    model: str | None = None,
    output_dir: Path | None = None,
    template_path: Path | None = None,
    max_retries: int = 2,
    include_base_three: bool = False,
) -> dict:
    """
    Extend RQ1 sample: rotate AML scenarios across empty template slots until
    `target_complete` entries have validator_pass (or slots exhausted).
    """
    if not llm_available():
        return {
            "status": "skipped",
            "reason": "No LLM API key",
            "hint": "export MIMO_API_KEY=tp-... or OPENAI_API_KEY=sk-...",
        }

    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    template = load_template(template_path)
    all_results: list[dict] = []

    next_batch_no = highest_batch_suffix(template, out_dir=out_dir) + 1

    if include_base_three:
        base = run_batch(
            model=model,
            output_dir=out_dir,
            template_path=template_path,
            max_retries=max_retries,
        )
        all_results.extend(base.get("results", []))
        template = load_template(template_path)

    while count_completed(template) < target_complete:
        slot = next_fill_index(template)
        if slot is None:
            break

        rotating = [(bp["slug"], i) for i, bp in enumerate(SCENARIO_BLUEPRINTS)]
        # Round-robin across the three AML scenarios as we fill successive template rows.
        slug, _bi = rotating[slot % 3]

        bn = next_batch_no
        next_batch_no += 1
        batch_suffix = f"{bn:03d}"
        adl_id = next_batch_adl_id_yaml_slug(slug, batch_suffix)

        blueprint = blueprint_for_slug(slug)
        task = blueprint["task"].format(adl_id=adl_id)
        out_name = f"llm_discovery_{slug}_batch{batch_suffix}.md"

        result = run_llm_sim(
            model=model,
            output_dir=out_dir,
            max_retries=max_retries,
            discovery_task=task,
            expected_adl_id=adl_id,
            output_name=out_name,
        )
        rel_path = ""
        vp = False
        if result.discovery_path:
            rp = (
                result.discovery_path.relative_to(ROOT)
                if result.discovery_path.is_relative_to(ROOT)
                else result.discovery_path
            )
            rel_path = str(rp)
            vp = result.status == "completed"

        apply_entry_at(
            template,
            slot,
            _entry_skeleton(
                adl_id=adl_id,
                scenario=blueprint["scenario"],
                discovery_path_rel=rel_path if rel_path else "",
                validator_pass=vp if rel_path else None,
                notes=(
                    "Track B MiMo expanded batch + Cursor proxy judges (batch id "
                    + batch_suffix
                    + "); Claude unavailable"
                ),
            ),
        )
        save_template(template, template_path)

        row = {"adl_id": adl_id, "slot": slot, **result.to_dict()}
        all_results.append(row)
        if result.events:
            write_llm_log(result, path=out_dir / f"llm_run_{slug}_batch{batch_suffix}.jsonl")

        if vp or rel_path:
            # Keep partial discovery_path on validator fail for auditing
            ent = template["entries"][slot]
            ent["discovery_path"] = rel_path
            ent["validator_pass"] = vp
            save_template(template, template_path)

    final_n = count_completed(template)
    return {
        "status": "completed" if final_n >= target_complete else "partial",
        "target_complete": target_complete,
        "n_completed_total": final_n,
        "results": all_results,
        "template_path": str(template_path or TEMPLATE_PATH),
    }


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Batch LLM discovery for RQ1 human eval")
    parser.add_argument("--model", default=None, help="LLM model override")
    parser.add_argument(
        "--template",
        default=str(TEMPLATE_PATH),
        help="Human eval template to update with discovery paths",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Directory for generated discovery markdown files",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Validator-aware retries for the LLM reviser (default: 2 with --target-complete, else 1).",
    )
    parser.add_argument(
        "--target-complete",
        type=int,
        default=None,
        help="Keep filling empty slots (rotating 3 AML scenarios) until this many validator_pass=true entries.",
    )
    parser.add_argument(
        "--redo-base-three",
        action="store_true",
        help="With --target-complete, regenerate the first three canonical scenarios before expanding.",
    )
    args = parser.parse_args(argv)
    max_retries = args.max_retries
    if max_retries is None:
        max_retries = 2 if args.target_complete is not None else 1

    if args.target_complete is not None:
        summary = run_batch_expand(
            target_complete=args.target_complete,
            model=args.model,
            output_dir=Path(args.output_dir),
            template_path=Path(args.template),
            max_retries=max_retries,
            include_base_three=args.redo_base_three,
        )
    else:
        summary = run_batch(
            model=args.model,
            output_dir=Path(args.output_dir),
            template_path=Path(args.template),
            max_retries=max_retries,
        )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
