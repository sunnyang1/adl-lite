---
adl_type: concept
adl_id: aml-casino
status: validated
confidence: 0.77
novelty: 0.24
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "赌场筹码洗钱"
  en: "Casino Chip Laundering"
evidence_refs:
  - vecdb://aml/aml_casino
---

# Casino Chip Laundering

> Status: 🟢 validated | Confidence: 77%

## Definition

**Casino Chip Laundering** converts cash to gaming chips and back to check or wire,
exploiting gaming CTR exemptions and minimal play time. Monitoring correlates buy-in,
table time, and cash-out across sessions and patron accounts.

## Monitoring Signals

- Chip purchase followed by cash-out within 2 hours with <30 minutes rated play
- Patron aggregate cash-in > declared gaming income capacity
- Structured chip buys below SAR threshold across multiple windows
- Collusion: coordinated buy-in/cash-out across linked patron IDs

## Related Concepts

- [[Cash Integration]] — cash-heavy integration channel
- [[CTR Threshold Avoidance]] — sub-threshold chip purchases

```adl:relation
source: "Casino Chip Laundering"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-cash-int"
mapping_type: ontological
confidence: 0.82
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_casino
description: "Chip buy-in / rated play / cash-out time ratio anomaly"
confidence: 0.79
observed_at: "2025-06-22T18:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: expert://aml_team/gaming_unit_2025
description: "Gaming compliance unit typology validation workshop"
confidence: 0.88
observed_at: "2025-09-01T14:00:00Z"
```
