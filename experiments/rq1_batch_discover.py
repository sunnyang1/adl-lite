"""
Optional batch LLM discovery runner for RQ1 human eval (3 AML scenarios).

Requires MIMO_API_KEY or OPENAI_API_KEY. Skips gracefully when no key is set.
"""

from __future__ import annotations

import json
from pathlib import Path

from .llm_harness import llm_available, run_llm_sim, write_llm_log

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "data" / "eval" / "human_rq1_template.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

SCENARIOS = [
    {
        "adl_id": "disc-llm-peripheral-trap",
        "slug": "peripheral-trap",
        "task": """\
Task: Write an ADL Lite discovery document about "Peripheral Attention Trap" in AML.
Output RAW markdown only — do NOT wrap the document in a ```markdown code fence.

Requirements:
- YAML front matter: adl_type: discovery, adl_id: disc-llm-peripheral-trap, domain: financial_aml,
  scope: private/ceiec-aml, status: provisional
- No pronouns: this, that, it, 这个, 那个
- At least one ```adl:relation block and one ```adl:evidence block
- evidence_type must be one of: vector_cluster, simulator_run, human_expert, cross_reference, empirical_observation
- Align monitoring signals with data/aml/concepts/aml-attention-trap.md (graph peripheral nodes, sink convergence)
""",
    },
    {
        "adl_id": "disc-llm-smurfing-pattern",
        "slug": "smurfing-pattern",
        "task": """\
Task: Write an ADL Lite discovery document about "Smurfing Pattern" in AML.
Output RAW markdown only — do NOT wrap the document in a ```markdown code fence.

Requirements:
- YAML front matter: adl_type: discovery, adl_id: disc-llm-smurfing-pattern, domain: financial_aml,
  scope: private/ceiec-aml, status: provisional
- No pronouns: this, that, it, 这个, 那个
- At least one ```adl:relation block and one ```adl:evidence block
- evidence_type must be one of: vector_cluster, simulator_run, human_expert, cross_reference, empirical_observation
- Align monitoring signals with data/aml/concepts/aml-smurfing.md (sub-threshold deposits, consolidation transfer)
""",
    },
    {
        "adl_id": "disc-llm-crypto-mixer",
        "slug": "crypto-mixer",
        "task": """\
Task: Write an ADL Lite discovery document about "Crypto Mixer Exposure" in AML.
Output RAW markdown only — do NOT wrap the document in a ```markdown code fence.

Requirements:
- YAML front matter: adl_type: discovery, adl_id: disc-llm-crypto-mixer, domain: financial_aml,
  scope: private/ceiec-aml, status: provisional
- No pronouns: this, that, it, 这个, 那个
- At least one ```adl:relation block and one ```adl:evidence block
- evidence_type must be one of: vector_cluster, simulator_run, human_expert, cross_reference, empirical_observation
- Align monitoring signals with data/aml/concepts/aml-crypto-mix.md (mixer contracts, peel-chain off-ramp)
""",
    },
]


def load_template(path: Path | None = None) -> dict:
    p = path or TEMPLATE_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def save_template(template: dict, path: Path | None = None) -> Path:
    p = path or TEMPLATE_PATH
    p.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    return p


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
    parser.add_argument("--max-retries", type=int, default=1)
    args = parser.parse_args(argv)

    summary = run_batch(
        model=args.model,
        output_dir=Path(args.output_dir),
        template_path=Path(args.template),
        max_retries=args.max_retries,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
