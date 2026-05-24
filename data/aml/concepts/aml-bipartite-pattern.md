---
adl_type: concept
adl_id: aml-bipartite-pattern
status: validated
confidence: 0.78
novelty: 0.45
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "图模式"
  en: "Bipartite Flow Pattern"
evidence_refs:
  - dataset://ibm/aml_hi_small/pattern/bipartite-pattern
  - vecdb://aml/aml_bipartite_pattern
---

# Bipartite Flow Pattern

> Status: validated | Confidence: 78%

## Definition

Two-partite sender-receiver roles with sparse cross edges; IBM bipartite motif. ADL Lite treats IBM HI-Small motifs as **concept anchors** for multi-agent
discovery and consensus—not as deployed transaction-scoring rules.

## Related Concepts

- [[Layering Chain]] — stack and cyclic motifs often follow layering typologies
- [[Smurfing Pattern]] — scatter-gather overlaps placement fragmentation

```adl:relation
source: "Bipartite Flow Pattern"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-mule-acct"
mapping_type: ontological
confidence: 0.80
```

```adl:evidence
evidence_type: cross_reference
data_ref: dataset://ibm/aml_hi_small/pattern/bipartite-pattern
description: "Mule hub connecting payers and collectors"
confidence: 0.75
observed_at: "2026-05-01T00:00:00Z"
```
