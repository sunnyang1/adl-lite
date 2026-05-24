---
adl_type: concept
adl_id: aml-random-baseline
status: validated
confidence: 0.78
novelty: 0.45
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "图模式"
  en: "Random Transaction Baseline"
evidence_refs:
  - dataset://ibm/aml_hi_small/pattern/random-baseline
  - vecdb://aml/aml_random_baseline
---

# Random Transaction Baseline

> Status: validated | Confidence: 78%

## Definition

Unstructured random transfers; IBM random baseline control motif. ADL Lite treats IBM HI-Small motifs as **concept anchors** for multi-agent
discovery and consensus—not as deployed transaction-scoring rules.

## Related Concepts

- [[Layering Chain]] — stack and cyclic motifs often follow layering typologies
- [[Smurfing Pattern]] — scatter-gather overlaps placement fragmentation

```adl:relation
source: "Random Transaction Baseline"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-random-baseline"
mapping_type: ontological
confidence: 0.80
```

```adl:relation
source: "Random Transaction Baseline"
relation: related-to
target: "adl://private/ceiec-aml/aml-smurfing"
mapping_type: domain
confidence: 0.40
```

```adl:evidence
evidence_type: cross_reference
data_ref: dataset://ibm/aml_hi_small/pattern/random-baseline
description: "Negative control for graph pattern retrieval benchmarks"
confidence: 0.75
observed_at: "2026-05-01T00:00:00Z"
```
