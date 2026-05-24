---
adl_type: concept
adl_id: aml-fan-in-pattern
status: validated
confidence: 0.78
novelty: 0.45
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "图模式"
  en: "Fan-In Graph Pattern"
evidence_refs:
  - dataset://ibm/aml_hi_small/pattern/fan-in-pattern
  - vecdb://aml/aml_fan_in_pattern
---

# Fan-In Graph Pattern

> Status: validated | Confidence: 78%

## Definition

Many sources converge to one sink; IBM AML fan-in motif in HI-Small synthetic graphs. ADL Lite treats IBM HI-Small motifs as **concept anchors** for multi-agent
discovery and consensus—not as deployed transaction-scoring rules.

## Related Concepts

- [[Layering Chain]] — stack and cyclic motifs often follow layering typologies
- [[Smurfing Pattern]] — scatter-gather overlaps placement fragmentation

```adl:relation
source: "Fan-In Graph Pattern"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-mule-acct"
mapping_type: ontological
confidence: 0.80
```

```adl:relation
source: "Fan-In Graph Pattern"
relation: isomorphic-to
target: "adl://private/ceiec-aml/aml-placement"
mapping_type: topological
confidence: 0.72
```

```adl:evidence
evidence_type: cross_reference
data_ref: dataset://ibm/aml_hi_small/pattern/fan-in-pattern
description: "Many-to-one transfer convergence in transaction graph analytics"
confidence: 0.75
observed_at: "2026-05-01T00:00:00Z"
```
