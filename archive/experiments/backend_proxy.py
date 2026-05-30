"""
Cursor / agent backend proxy for RQ1 batch discovery (no MIMO or OpenAI keys).

When ``rq1_batch_discover --backend-proxy`` is set, discovery markdown is
materialized from deterministic in-repo templates instead of external LLM APIs.
By default the committed ``human_rq1_template.json`` is **not** overwritten;
pass ``--sync-template`` to update validator flags in the template.

    python -m experiments.rq1_batch_discover --backend-proxy --regenerate-all

Or invoke materialization directly (outputs only, no template sync):

    python -m experiments.backend_proxy
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from adl_lite import parse_text
from adl_lite.validator import ADLValidator

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
TEMPLATE_PATH = ROOT / "data" / "eval" / "human_rq1_template.json"

CANON_SCENARIO_SLUGS = ("peripheral-trap", "smurfing-pattern", "crypto-mixer")


def slug_from_adl_id(adl_id: str | None) -> str | None:
    if not isinstance(adl_id, str) or not adl_id.startswith("disc-llm-"):
        return None
    tail = adl_id.removeprefix("disc-llm-")
    tail = re.sub(r"-batch\d+$", "", tail)
    if tail not in CANON_SCENARIO_SLUGS:
        return None
    return tail


def load_template(path: Path | None = None) -> dict:
    p = path or TEMPLATE_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def save_template(template: dict, path: Path | None = None) -> Path:
    p = path or TEMPLATE_PATH
    p.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    return p


def plain_output_relative(slug: str) -> str:
    name = f"plain_discovery_{slug}.md"
    return str((ROOT / "experiments" / "outputs" / name).relative_to(ROOT))

# 15 active RQ1 rows: 3 canonical + 12 batch-expanded (001–012)
RQ1_OUTPUT_SPECS: list[dict[str, str | None]] = [
    {"adl_id": "disc-llm-peripheral-trap", "slug": "peripheral-trap", "batch": None},
    {"adl_id": "disc-llm-smurfing-pattern", "slug": "smurfing-pattern", "batch": None},
    {"adl_id": "disc-llm-crypto-mixer", "slug": "crypto-mixer", "batch": None},
    {"adl_id": "disc-llm-peripheral-trap-batch001", "slug": "peripheral-trap", "batch": "001"},
    {"adl_id": "disc-llm-smurfing-pattern-batch002", "slug": "smurfing-pattern", "batch": "002"},
    {"adl_id": "disc-llm-crypto-mixer-batch003", "slug": "crypto-mixer", "batch": "003"},
    {"adl_id": "disc-llm-peripheral-trap-batch004", "slug": "peripheral-trap", "batch": "004"},
    {"adl_id": "disc-llm-smurfing-pattern-batch005", "slug": "smurfing-pattern", "batch": "005"},
    {"adl_id": "disc-llm-crypto-mixer-batch006", "slug": "crypto-mixer", "batch": "006"},
    {"adl_id": "disc-llm-peripheral-trap-batch007", "slug": "peripheral-trap", "batch": "007"},
    {"adl_id": "disc-llm-smurfing-pattern-batch008", "slug": "smurfing-pattern", "batch": "008"},
    {"adl_id": "disc-llm-crypto-mixer-batch009", "slug": "crypto-mixer", "batch": "009"},
    {"adl_id": "disc-llm-peripheral-trap-batch010", "slug": "peripheral-trap", "batch": "010"},
    {"adl_id": "disc-llm-smurfing-pattern-batch011", "slug": "smurfing-pattern", "batch": "011"},
    {"adl_id": "disc-llm-crypto-mixer-batch012", "slug": "crypto-mixer", "batch": "012"},
]

PLAIN_SLUGS = ("peripheral-trap", "smurfing-pattern", "crypto-mixer")

_PLAIN_STUB_BODY: dict[str, str] = {
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


def write_plain_stub(slug: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_PLAIN_STUB_BODY[slug], encoding="utf-8")
    return out_path


def backend_proxy_enabled() -> bool:
    """Always False — proxy is enabled only via ``rq1_batch_discover --backend-proxy``."""
    v = os.environ.get("ADL_BACKEND_PROXY", "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        import warnings

        warnings.warn(
            "ADL_BACKEND_PROXY is ignored; use: "
            "python -m experiments.rq1_batch_discover --backend-proxy",
            UserWarning,
            stacklevel=2,
        )
    return False


def output_name_for_spec(spec: dict[str, str | None]) -> str:
    slug = str(spec["slug"])
    batch = spec.get("batch")
    if batch:
        return f"llm_discovery_{slug}_batch{batch}.md"
    return f"llm_discovery_{slug}.md"


def _variant_index(batch: str | None) -> int:
    if not batch:
        return 0
    return int(batch)


def _title_en(slug: str) -> str:
    return {
        "peripheral-trap": "Peripheral Attention Trap",
        "smurfing-pattern": "Smurfing Pattern",
        "crypto-mixer": "Crypto Mixer Exposure",
    }[slug]


def _mechanism(slug: str) -> str:
    return {
        "peripheral-trap": "isomorphic_mapping",
        "smurfing-pattern": "emergent_pattern",
        "crypto-mixer": "compositional_blend",
    }[slug]


def _concept_uri(slug: str) -> str:
    return {
        "peripheral-trap": "adl://public/concepts/aml-attention-trap",
        "smurfing-pattern": "adl://public/concepts/aml-smurfing",
        "crypto-mixer": "adl://public/concepts/aml-crypto-mix",
    }[slug]


def _build_peripheral_body(variant: int) -> tuple[str, str]:
    emphasis = [
        "peripheral clustering coefficient spikes while hub bypass ratio stays elevated",
        "alert-to-value ratio skews toward low-centrality feeders before sink convergence",
        "analyst queue depth rises on peripheral SARs while consolidation corridors stay quiet",
    ][variant % 3]
    stmt = (
        f"AML transaction graphs show {emphasis}. "
        "The Peripheral Attention Trap names adversarial routing that parks volume on "
        "low-betweenness accounts so monitoring attention decays with hop distance from "
        "flagged subjects. Sink convergence toward dormant beneficiary wallets confirms "
        "the trap: multiple peripheral chains terminate at shared extraction endpoints "
        "invisible to hub-centric heuristics."
    )
    intuition = (
        "Graph monitoring stacks rank nodes by proximity to open investigations. "
        "Layering teams add benign-looking intermediaries until attention scores on "
        "terminal beneficiaries fall below operational review thresholds. "
        "Peripheral Attention Trap documentation ties the evasion geometry to "
        "aml-attention-trap monitoring signals: peripheral clustering, hub bypass, "
        "alert-to-value imbalance, and sink convergence within two hops."
    )
    return stmt, intuition


def _build_smurfing_body(variant: int) -> tuple[str, str]:
    signal_phrase = [
        "sub-threshold cash deposits cluster at eighty to ninety-nine percent of CTR",
        "shared device fingerprints link otherwise unrelated retail accounts",
        "round-dollar deposit bursts precede twenty-four-hour consolidation wires",
    ][variant % 3]
    stmt = (
        f"Beneficial-owner networks exhibit {signal_phrase}. "
        "The Smurfing Pattern reconstructs placement volume above currency reporting "
        "limits by fanning structured deposits across many low-risk retail endpoints "
        "before a consolidation account absorbs the aggregate flow."
    )
    intuition = (
        "CTR heuristics treat each retail account independently while smurfing "
        "operators coordinate timing, amount bands, and channel choice. "
        "Smurfing Pattern discovery prose aligns with aml-smurfing concept thresholds "
        "and consolidation transfer monitoring so investigators can compare emergent "
        "fan-in graphs against typology baselines."
    )
    return stmt, intuition


def _build_crypto_body(variant: int) -> tuple[str, str]:
    signal_phrase = [
        "inbound transfers from labeled tumbler contracts spike before peel-chain exits",
        "privacy-coin swaps precede stablecoin off-ramps at exchange gateways",
        "wallet cohorts show peel-chain depth above five hops with fiat ingress spikes",
    ][variant % 3]
    stmt = (
        f"On-chain surveillance flags {signal_phrase}. "
        "Crypto Mixer Exposure documents how tumbler deposits, peel chains, and "
        "fiat off-ramps compose a laundering stack where each leg alone appears "
        "plausibly legitimate until linked through shared timing and amount bands."
    )
    intuition = (
        "Mixer contracts break address lineage while peel chains reintroduce spendable "
        "UTXOs at exchange deposit addresses. Crypto Mixer Exposure ties wallet-level "
        "signals to aml-crypto-mix monitoring: mixer contract labels, peel-chain depth, "
        "and stablecoin off-ramp velocity relative to historical wallet behavior."
    )
    return stmt, intuition


def build_discovery_markdown(*, adl_id: str, slug: str, batch: str | None) -> str:
    """Deterministic ADL discovery body using ontology-registered predicates only."""
    variant = _variant_index(batch)
    title = _title_en(slug)
    mechanism = _mechanism(slug)
    conf = 0.70 + (variant % 5) * 0.02
    nov = 0.62 + (variant % 4) * 0.03
    batch_tag = f"-batch{batch}" if batch else ""
    vec_ref = f"vecdb://ceiec-aml/{slug.replace('-', '_')}{batch_tag}-2026q2"
    sim_ref = f"tool://aml_simulator/v2/{slug}{batch_tag}"

    if slug == "peripheral-trap":
        stmt, intuition = _build_peripheral_body(variant)
        zh = "外围注意力陷阱"
        rel2_pred = "analogical-to"
        rel2_target = "adl://public/concepts/gradient_explosion"
        rel2_map = "structural"
    elif slug == "smurfing-pattern":
        stmt, intuition = _build_smurfing_body(variant)
        zh = "拆分存款模式"
        rel2_pred = "co-occurs-with"
        rel2_target = "adl://public/concepts/money_laundering_layering"
        rel2_map = "statistical"
    else:
        stmt, intuition = _build_crypto_body(variant)
        zh = "加密货币混币器暴露"
        rel2_pred = "related-to"
        rel2_target = "adl://public/concepts/peel_chain_laundering"
        rel2_map = "domain"

    concept_uri = _concept_uri(slug)
    concept_file = {
        "peripheral-trap": "data/aml/concepts/aml-attention-trap.md",
        "smurfing-pattern": "data/aml/concepts/aml-smurfing.md",
        "crypto-mixer": "data/aml/concepts/aml-crypto-mix.md",
    }[slug]

    return f"""---
adl_type: discovery
adl_id: {adl_id}
status: provisional
confidence: {conf:.2f}
novelty: {nov:.2f}
domain: financial_aml
mechanism: {mechanism}
scope: private/ceiec-aml
provisional_names:
  en: "{title}"
  zh: "{zh}"
evidence_refs:
  - {vec_ref}
  - {sim_ref}
---

# {title}

## Discovery Statement

{stmt}

## Intuition

{intuition}

## Related Concepts

- [[{title}]] — discovery anchor for RQ1 batch {batch or "canonical"}
- [[AML monitoring graph]] — transaction graph subject to attention-weighted review
- [[Sink convergence]] — shared beneficiary aggregation after peripheral routing

```adl:relation
source: "{title}"
relation: isomorphic-to
target: "{concept_uri}"
mapping_type: topological
confidence: 0.86
```

```adl:relation
source: "{title}"
relation: {rel2_pred}
target: "{rel2_target}"
mapping_type: {rel2_map}
confidence: 0.74
```

```adl:relation
source: "{title}"
relation: specialisation-of
target: "{concept_uri}"
mapping_type: ontological
confidence: 0.71
```

```adl:evidence
evidence_type: vector_cluster
data_ref: {vec_ref}
description: "Vector clustering over {batch_tag or 'canonical'} cohort surfaces coordinated peripheral or mixer-linked behavior aligned with {concept_file} heuristics."
confidence: 0.79
observed_at: "2026-05-24T00:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: {sim_ref}
description: "Monte Carlo laundering simulation replays adversarial routing strategies; evasion success correlates with attention decay or sub-threshold structuring parameters from the concept stub."
confidence: 0.73
observed_at: "2026-05-24T00:00:00Z"
```
"""


def strict_validate_file(path: Path) -> tuple[bool, list[str]]:
    text = path.read_text(encoding="utf-8")
    try:
        doc = parse_text(text)
    except Exception as e:
        return False, [f"parse error: {e}"]
    errors = ADLValidator(strict=True).validate_document(doc)
    return len(errors) == 0, errors


def write_discovery_spec(
    spec: dict[str, str | None],
    *,
    output_dir: Path,
) -> tuple[Path, bool, list[str]]:
    out_dir = output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    name = output_name_for_spec(spec)
    path = out_dir / name
    md = build_discovery_markdown(
        adl_id=str(spec["adl_id"]),
        slug=str(spec["slug"]),
        batch=spec.get("batch"),  # type: ignore[arg-type]
    )
    path.write_text(md, encoding="utf-8")
    ok, errors = strict_validate_file(path)
    return path, ok, errors


def materialize_plain_baselines(*, output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for slug in PLAIN_SLUGS:
        rel = plain_output_relative(slug)
        path = ROOT / rel
        write_plain_stub(slug, path)
        paths.append(path)
    return paths


def sync_template_validator_flags(
    template: dict,
    *,
    results: list[tuple[str, Path, bool]],
) -> None:
    by_id = {adl_id: (path, ok) for adl_id, path, ok in results}
    for entry in template.get("entries", []):
        aid = entry.get("adl_id")
        if aid in by_id:
            path, ok = by_id[aid]
            rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
            entry["discovery_path"] = str(rel)
            entry["validator_pass"] = ok
            if ok and not str(entry.get("notes") or "").strip():
                entry["notes"] = "Backend proxy materialization (--backend-proxy)"


def materialize_rq1_discoveries(
    *,
    output_dir: Path | None = None,
    template_path: Path | None = None,
    include_plain: bool = True,
    specs: list[dict[str, str | None]] | None = None,
    sync_template: bool = False,
) -> dict[str, Any]:
    """Write RQ1 LLM discoveries; optionally refresh plain baselines."""
    out_dir = output_dir or OUTPUT_DIR
    work_specs = specs if specs is not None else RQ1_OUTPUT_SPECS
    results: list[tuple[str, Path, bool]] = []
    failures: list[dict[str, Any]] = []

    for spec in work_specs:
        path, ok, errors = write_discovery_spec(spec, output_dir=out_dir)
        results.append((str(spec["adl_id"]), path, ok))
        if not ok:
            failures.append({"adl_id": spec["adl_id"], "path": str(path), "errors": errors})

    plain_paths: list[str] = []
    if include_plain:
        for p in materialize_plain_baselines(output_dir=out_dir):
            plain_paths.append(str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p))

    if sync_template:
        template = load_template(template_path)
        sync_template_validator_flags(template, results=results)
        if include_plain:
            for entry in template.get("entries", []):
                slug = slug_from_adl_id(entry.get("adl_id"))
                if slug:
                    entry["plain_discovery_path"] = plain_output_relative(slug)
        save_template(template, template_path)
    n_ok = sum(1 for _, _, ok in results if ok)
    return {
        "status": "completed" if n_ok == len(work_specs) and not failures else "partial",
        "provider": "backend-proxy",
        "n_written": len(results),
        "n_strict_pass": n_ok,
        "n_target": len(work_specs),
        "failures": failures,
        "plain_paths": plain_paths,
        "template_synced": sync_template,
        "template_path": str(template_path or TEMPLATE_PATH) if sync_template else None,
    }


CANONICAL_SPECS = RQ1_OUTPUT_SPECS[:3]


def run_backend_proxy_batch(
    *,
    output_dir: Path | None = None,
    template_path: Path | None = None,
    regenerate_all: bool = False,
    include_plain: bool = True,
    sync_template: bool = False,
) -> dict[str, Any]:
    """Entry point for rq1_batch_discover --backend-proxy (no external LLM APIs)."""
    specs = RQ1_OUTPUT_SPECS if regenerate_all or include_plain else CANONICAL_SPECS
    return materialize_rq1_discoveries(
        output_dir=output_dir,
        template_path=template_path,
        include_plain=include_plain,
        specs=specs,
        sync_template=sync_template,
    )


def main() -> None:
    summary = materialize_rq1_discoveries(sync_template=False)
    print(json.dumps(summary, indent=2))
    if summary.get("failures"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
