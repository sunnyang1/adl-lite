---
adl_type: concept
adl_id: aml-gather-scatter
status: validated
confidence: 0.78
novelty: 0.45
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "图模式"
  en: "Gather-Scatter Pattern"
evidence_refs:
  - dataset://ibm/aml_hi_small/pattern/gather-scatter
  - vecdb://aml/aml_gather_scatter
---

# Gather-Scatter Pattern

> Status: validated | Confidence: 78%

## Definition

Funds gather then scatter across accounts; IBM gather-scatter motif. ADL Lite treats IBM HI-Small motifs as **concept anchors** for multi-agent
discovery and consensus—not as deployed transaction-scoring rules.

## Related Concepts

- [[Layering Chain]] — stack and cyclic motifs often follow layering typologies
- [[Smurfing Pattern]] — scatter-gather overlaps placement fragmentation

```adl:relation
source: "Gather-Scatter Pattern"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-smurfing"
mapping_type: ontological
confidence: 0.80
```

```adl:relation
source: "Gather-Scatter Pattern"
relation: isomorphic-to
target: "adl://private/ceiec-aml/aml-scatter-gather"
mapping_type: topological
confidence: 0.72
```

```adl:evidence
evidence_type: cross_reference
data_ref: dataset://ibm/aml_hi_small/pattern/gather-scatter
description: "Sequential consolidation then multi-leg exit"
confidence: 0.75
observed_at: "2026-05-01T00:00:00Z"
```
