"""AML mini-dataset loader and generator."""

from __future__ import annotations

import json
from pathlib import Path

from adl_lite import ADLMemory, parse_file

DATA_DIR = Path(__file__).resolve().parent
CONCEPTS_DIR = DATA_DIR / "concepts"
MANIFEST_PATH = DATA_DIR / "manifest.json"
QUERIES_PATH = DATA_DIR / "queries.json"

CONCEPT_TOPICS = [
    ("aml-smurfing", "Smurfing Pattern", "Structuring via many small deposits"),
    ("aml-layering", "Layering Chain", "Multi-hop obfuscation of fund origin"),
    ("aml-shell-co", "Shell Company Network", "Paper entities routing illicit flows"),
    ("aml-trade-mis", "Trade Misinvoicing", "Over/under invoicing for value transfer"),
    ("aml-crypto-mix", "Crypto Mixer Exposure", "On-chain tumbler interaction signals"),
    ("aml-pep-link", "PEP Association", "Politically exposed person proximity"),
    ("aml-rapid-move", "Rapid Movement", "Same-day cross-border velocity anomaly"),
    ("aml-cash-int", "Cash Integration", "Placement into legitimate business cash flow"),
    ("aml-ben-owner", "Beneficial Owner Gap", "Ownership opacity vs transaction volume"),
    ("aml-round-trip", "Round Trip Transfer", "Funds exit and re-enter same jurisdiction"),
    ("aml-ctr-avoid", "CTR Threshold Avoidance", "Deposits clustered just below reporting"),
    ("aml-mule-acct", "Money Mule Account", "Third-party account used as pass-through"),
    ("aml-trade-base", "Trade-Based ML", "Commodity invoice manipulation"),
    ("aml-casino", "Casino Chip Laundering", "Gaming instrument conversion path"),
    ("aml-real-estate", "Real Estate ML", "Property purchase opacity patterns"),
    ("aml-hawala", "Informal Value Transfer", "Hawala-like off-ledger settlement"),
    ("aml-nesting", "Nested Correspondent", "Nested account layering in correspondent banks"),
    ("aml-virtual-asset", "Virtual Asset Gateway", "Fiat on-ramp off-ramp cycling"),
    ("aml-trade-loop", "Circular Trade Loop", "Closed loop invoice cycles"),
    ("aml-attention-trap", "Peripheral Attention Trap", "Peripheral node concentration pattern"),
    ("aml-placement", "Placement Stage", "FATF placement stage typology"),
    ("aml-integration", "Integration Stage", "FATF integration stage typology"),
    ("aml-structuring", "Structuring Typology", "General structuring below reporting thresholds"),
    ("aml-cuckoo-smurf", "Cuckoo Smurfing", "Victim-account smurfing variant"),
    ("aml-nominee-acct", "Nominee Account", "Stand-in account holder obscuring UBO"),
    ("aml-fan-in-pattern", "Fan-In Graph Pattern", "IBM HI-Small fan-in graph motif"),
    ("aml-fan-out-pattern", "Fan-Out Graph Pattern", "IBM HI-Small fan-out graph motif"),
    ("aml-gather-scatter", "Gather-Scatter Pattern", "IBM gather-scatter graph motif"),
    ("aml-scatter-gather", "Scatter-Gather Pattern", "IBM scatter-gather graph motif"),
    ("aml-bipartite-pattern", "Bipartite Flow Pattern", "IBM bipartite graph motif"),
    ("aml-cyclic-pattern", "Cyclic Transfer Pattern", "IBM cyclic graph motif"),
    ("aml-stack-pattern", "Stacked Layer Pattern", "IBM stack graph motif"),
    ("aml-random-baseline", "Random Transaction Baseline", "IBM random control motif"),
]

QUERIES = [
    {"id": "q01", "text": "small deposit structuring smurfing", "relevant": ["aml-smurfing"]},
    {"id": "q02", "text": "multi hop layering obfuscation", "relevant": ["aml-layering"]},
    {"id": "q03", "text": "shell company paper entity", "relevant": ["aml-shell-co"]},
    {"id": "q04", "text": "trade misinvoicing over invoice", "relevant": ["aml-trade-mis"]},
    {"id": "q05", "text": "crypto mixer tumbler blockchain", "relevant": ["aml-crypto-mix"]},
    {"id": "q06", "text": "politically exposed person pep", "relevant": ["aml-pep-link"]},
    {"id": "q07", "text": "rapid cross border movement velocity", "relevant": ["aml-rapid-move"]},
    {"id": "q08", "text": "cash integration legitimate business", "relevant": ["aml-cash-int"]},
    {"id": "q09", "text": "beneficial owner opacity ubo", "relevant": ["aml-ben-owner"]},
    {"id": "q10", "text": "round trip funds re-enter jurisdiction", "relevant": ["aml-round-trip"]},
    {"id": "q11", "text": "ctr threshold avoidance reporting limit", "relevant": ["aml-ctr-avoid"]},
    {"id": "q12", "text": "money mule pass through account", "relevant": ["aml-mule-acct"]},
    {"id": "q13", "text": "trade based laundering commodity", "relevant": ["aml-trade-base"]},
    {"id": "q14", "text": "casino chip gaming conversion", "relevant": ["aml-casino"]},
    {
        "id": "q15",
        "text": "peripheral node attention trap concentration",
        "relevant": ["aml-attention-trap", "aml-layering"],
    },
]


def _concept_md(adl_id: str, en_name: str, description: str) -> str:
    slug = adl_id.replace("-", "_")
    return f"""---
adl_type: concept
adl_id: {adl_id}
status: validated
confidence: 0.75
novelty: 0.35
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  en: "{en_name}"
evidence_refs:
  - vecdb://aml/{slug}
---

# {en_name}

## Definition

{description} in anti-money laundering monitoring contexts.

## Related Concepts

- [[Capital Attention Trap]] — cross-domain structural analogy

```adl:relation
source: "{en_name}"
relation: related-to
target: "adl://private/ceiec-aml/disc-capital-trap"
mapping_type: domain
confidence: 0.70
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/{slug}
description: "AML feature cluster for {en_name.lower()}"
confidence: 0.72
observed_at: "2026-05-01T00:00:00Z"
```
"""


def ensure_dataset() -> Path:
    """Generate concept stubs if missing; preserve curated manifest and queries."""
    CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)

    concepts = []
    for adl_id, en_name, desc in CONCEPT_TOPICS:
        rel_path = f"concepts/{adl_id}.md"
        full = DATA_DIR / rel_path
        if not full.exists():
            full.write_text(_concept_md(adl_id, en_name, desc), encoding="utf-8")
        concepts.append(
            {
                "adl_id": adl_id,
                "path": rel_path,
                "domain": "financial_aml",
                "scope": "private/ceiec-aml",
            }
        )

    if not MANIFEST_PATH.exists():
        MANIFEST_PATH.write_text(
            json.dumps(
                {"version": "0.1", "count": len(concepts), "concepts": concepts},
                indent=2,
            ),
            encoding="utf-8",
        )

    if not QUERIES_PATH.exists():
        QUERIES_PATH.write_text(
            json.dumps({"version": "0.1", "queries": QUERIES}, indent=2),
            encoding="utf-8",
        )
    return DATA_DIR


def load_manifest() -> dict:
    ensure_dataset()
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_queries() -> list[dict]:
    ensure_dataset()
    data = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    return data["queries"]


def index_all(db_path: str | Path) -> ADLMemory:
    """Parse and index all AML concepts into ADLMemory."""
    ensure_dataset()
    mem = ADLMemory(db_path=str(db_path))
    for entry in load_manifest()["concepts"]:
        doc = parse_file(DATA_DIR / entry["path"])
        mem.store(doc)
    return mem
