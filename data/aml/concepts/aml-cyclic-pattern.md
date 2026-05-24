---
adl_type: concept
adl_id: aml-cyclic-pattern
status: validated
confidence: 0.78
novelty: 0.45
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "图模式"
  en: "Cyclic Transfer Pattern"
evidence_refs:
  - dataset://ibm/aml_hi_small/pattern/cyclic-pattern
  - vecdb://aml/aml_cyclic_pattern
---

# Cyclic Transfer Pattern

> Status: validated | Confidence: 78%

## Definition

Closed loop transfers revisiting accounts; IBM cyclic motif. ADL Lite treats IBM HI-Small motifs as **concept anchors** for multi-agent
discovery and consensus—not as deployed transaction-scoring rules.

## Related Concepts

- [[Layering Chain]] — stack and cyclic motifs often follow layering typologies
- [[Smurfing Pattern]] — scatter-gather overlaps placement fragmentation

```adl:relation
source: "Cyclic Transfer Pattern"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-round-trip"
mapping_type: ontological
confidence: 0.80
```

```adl:relation
source: "Cyclic Transfer Pattern"
relation: isomorphic-to
target: "adl://private/ceiec-aml/aml-trade-loop"
mapping_type: topological
confidence: 0.72
```

```adl:evidence
evidence_type: cross_reference
data_ref: dataset://ibm/aml_hi_small/pattern/cyclic-pattern
description: "Cycle length and value conservation anomalies"
confidence: 0.75
observed_at: "2026-05-01T00:00:00Z"
```
