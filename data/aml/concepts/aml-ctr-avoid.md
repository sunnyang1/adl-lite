---
adl_type: concept
adl_id: aml-ctr-avoid
status: validated
confidence: 0.83
novelty: 0.30
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "规避大额交易报告"
  en: "CTR Threshold Avoidance"
evidence_refs:
  - vecdb://aml/aml_ctr_avoid
  - regulatory://bsa/ctr_guidance
---

# CTR Threshold Avoidance

> Status: 🟢 validated | Confidence: 83%

## Definition

**CTR Threshold Avoidance** structures cash activity to remain just below Currency Transaction
Report limits while aggregate volume exceeds reporting intent. Algorithms detect clustered
deposits, split counter parties, and temporal bundling across branches.

## Monitoring Signals

- Deposit amounts in 90–99% band of CTR for ≥5 occurrences / 30 days
- Multiple branches same depositor fingerprint same day
- Aggregated same-beneficiary inflow >CTR within 48h rolling window
- Withdrawal immediately after sub-threshold deposit chain

## Related Concepts

- [[Smurfing Pattern]] — general structuring parent pattern

```adl:relation
source: "CTR Threshold Avoidance"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-smurfing"
mapping_type: ontological
confidence: 0.91
```

```adl:evidence
evidence_type: cross_reference
data_ref: regulatory://bsa/ctr_guidance
description: "BSA CTR structuring red-flag alignment"
confidence: 0.89
observed_at: "2025-01-01T00:00:00Z"
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_ctr_avoid
description: "Histogram spike below CTR with beneficiary consolidation"
confidence: 0.84
observed_at: "2025-11-20T08:00:00Z"
```
