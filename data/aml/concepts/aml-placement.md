---
adl_type: concept
adl_id: aml-placement
status: validated
confidence: 0.88
novelty: 0.15
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "放置阶段"
  en: "Placement Stage"
evidence_refs:
  - regulatory://fatf/placement
  - vecdb://aml/aml_placement
---

# Placement Stage

> Status: validated | Confidence: 88%

## Definition

The **Placement Stage** introduces illicit proceeds into the formal financial system or
parallel banking channels. Typologies include bulk cash deposit, smurfed sub-threshold
entries, trade-finance over-invoicing, and virtual-asset on-ramps. Placement leaves
the highest physical-cash and CTR-adjacent footprint of the three classic ML stages.

## Related Concepts

- [[Smurfing Pattern]] — common placement technique
- [[Cash Integration]] — placement into operating business cash flow
- [[CTR Threshold Avoidance]] — placement shaped to evade reporting

```adl:relation
source: "Placement Stage"
relation: specialisation-of
target: "adl://public/concepts/money_laundering_placement"
mapping_type: ontological
confidence: 0.95
```

```adl:relation
source: "Placement Stage"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-smurfing"
mapping_type: statistical
confidence: 0.82
```

```adl:evidence
evidence_type: cross_reference
data_ref: regulatory://fatf/placement
description: "FATF placement typology anchor"
confidence: 0.92
observed_at: "2025-01-01T00:00:00Z"
```
