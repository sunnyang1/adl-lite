---
adl_type: concept
adl_id: aml-stack-pattern
status: validated
confidence: 0.78
novelty: 0.45
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "图模式"
  en: "Stacked Layer Pattern"
evidence_refs:
  - dataset://ibm/aml_hi_small/pattern/stack-pattern
  - vecdb://aml/aml_stack_pattern
---

# Stacked Layer Pattern

> Status: validated | Confidence: 78%

## Definition

Linear depth-first transfer stack; IBM stack motif. ADL Lite treats IBM HI-Small motifs as **concept anchors** for multi-agent
discovery and consensus—not as deployed transaction-scoring rules.

## Related Concepts

- [[Layering Chain]] — stack and cyclic motifs often follow layering typologies
- [[Smurfing Pattern]] — scatter-gather overlaps placement fragmentation

```adl:relation
source: "Stacked Layer Pattern"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-layering"
mapping_type: ontological
confidence: 0.80
```

```adl:relation
source: "Stacked Layer Pattern"
relation: isomorphic-to
target: "adl://private/ceiec-aml/aml-nesting"
mapping_type: topological
confidence: 0.72
```

```adl:evidence
evidence_type: cross_reference
data_ref: dataset://ibm/aml_hi_small/pattern/stack-pattern
description: "Depth-first chain without wide fan"
confidence: 0.75
observed_at: "2026-05-01T00:00:00Z"
```
