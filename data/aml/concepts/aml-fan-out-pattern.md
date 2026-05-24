---
adl_type: concept
adl_id: aml-fan-out-pattern
status: validated
confidence: 0.78
novelty: 0.45
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "图模式"
  en: "Fan-Out Graph Pattern"
evidence_refs:
  - dataset://ibm/aml_hi_small/pattern/fan-out-pattern
  - vecdb://aml/aml_fan_out_pattern
---

# Fan-Out Graph Pattern

> Status: validated | Confidence: 78%

## Definition

One source disperses to many destinations; IBM AML fan-out motif. ADL Lite treats IBM HI-Small motifs as **concept anchors** for multi-agent
discovery and consensus—not as deployed transaction-scoring rules.

## Related Concepts

- [[Layering Chain]] — stack and cyclic motifs often follow layering typologies
- [[Smurfing Pattern]] — scatter-gather overlaps placement fragmentation

```adl:relation
source: "Fan-Out Graph Pattern"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-integration"
mapping_type: ontological
confidence: 0.80
```

```adl:relation
source: "Fan-Out Graph Pattern"
relation: isomorphic-to
target: "adl://private/ceiec-aml/aml-layering"
mapping_type: topological
confidence: 0.72
```

```adl:evidence
evidence_type: cross_reference
data_ref: dataset://ibm/aml_hi_small/pattern/fan-out-pattern
description: "One-to-many disbursement burst after layering"
confidence: 0.75
observed_at: "2026-05-01T00:00:00Z"
```
