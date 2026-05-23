# Write ADL Lite discovery documents (batch)

Produce **three valid Markdown discovery files** for AML scenarios below. Each file must have L1 YAML front matter, L2 prose, and L3 `adl:*` blocks.

## Required structure (per document)

```markdown
---
adl_type: discovery
adl_id: disc-<slug>
status: provisional
confidence: 0.0-1.0
novelty: 0.0-1.0
domain: financial_aml
mechanism: isomorphic_mapping | analogical_transfer | compositional_blend | abstract_generalisation | emergent_pattern
scope: private/ceiec-aml
provisional_names:
  en: "English Name"
evidence_refs:
  - vecdb://...
---

# Title

## Discovery Statement
<One paragraph. No pronouns: never use "this", "that", "it", "these", "those".>

## Intuition
<Optional explanatory prose with explicit concept names.>

## Related Concepts
- [[Related Concept]] — brief note

```adl:relation
source: "Concept Name"
relation: isomorphic-to
target: "adl://public/concepts/<target_slug>"
mapping_type: topological
confidence: 0.85
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://...
description: "..."
confidence: 0.80
observed_at: "2026-05-23T00:00:00Z"
```
```

## Rules

1. **No forbidden pronouns** in L2 body (English or Chinese).
2. **Discovery** documents must include `mechanism`.
3. At least **one** `adl:relation` and **one** `adl:evidence` block per document.
4. Use `adl://` URIs for cross-scope targets when linking public concepts.
5. Keep `adl_id` lowercase alphanumeric with hyphens/underscores only.
6. After writing, run validation mentally: would `adl-lite validate` pass?

## Scenario 1 — Peripheral Attention Trap

- **adl_id:** `disc-llm-peripheral-trap`
- **Concept anchor:** Peripheral Attention Trap
- **Reference:** `data/aml/concepts/aml-attention-trap.md`
- **Signals:** peripheral clustering coefficient, hub bypass ratio, alert-to-value ratio, sink convergence
- **Mechanism hint:** topologically isomorphic to gradient explosion (peripheral noise vs consolidating corridor)

## Scenario 2 — Smurfing Pattern

- **adl_id:** `disc-llm-smurfing-pattern`
- **Concept anchor:** Smurfing Pattern
- **Reference:** `data/aml/concepts/aml-smurfing.md`
- **Signals:** sub-threshold deposits (80–99% of CTR), shared device fingerprint, round-dollar amounts, 24h consolidation transfer
- **Mechanism hint:** emergent_pattern — aggregate flow reconstructs placement volume above reporting limits

## Scenario 3 — Crypto Mixer Exposure

- **adl_id:** `disc-llm-crypto-mixer`
- **Concept anchor:** Crypto Mixer Exposure
- **Reference:** `data/aml/concepts/aml-crypto-mix.md`
- **Signals:** inbound from labeled mixer contracts, peel-chain outbound, privacy-coin swap then stablecoin off-ramp
- **Mechanism hint:** compositional_blend — crypto leg combined with fiat off-ramp spike

## Output

Return three documents separated by a line containing only `---FILE---`. No commentary. Do not wrap documents in ` ```markdown ` code fences.

Order: Scenario 1, Scenario 2, Scenario 3.

## MiMo / API

When using Xiaomi MiMo Token Plan (`tp-` key):

```bash
export MIMO_API_KEY=tp-...
export MIMO_API_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
export MIMO_MODEL=mimo-v2.5-pro
python -m experiments.rq1_batch_discover
```
