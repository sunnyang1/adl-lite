---
adl_type: concept
adl_id: aml-structuring
status: validated
confidence: 0.84
novelty: 0.22
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "结构化交易"
  en: "Structuring Typology"
evidence_refs:
  - regulatory://fatf/rec16_structuring
  - vecdb://aml/aml_structuring
---

# Structuring Typology

> Status: validated | Confidence: 84%

## Definition

**Structuring** deliberately fragments transactions to avoid record-keeping, CTR filing,
or internal threshold alerts while preserving aggregate economic effect. Structuring spans
cash and wire modalities; smurfing and CTR avoidance are operational specialisations.
Monitoring compares rolling-window aggregates to per-leg amounts.

## Related Concepts

- [[Smurfing Pattern]] — cash-side structuring specialisation
- [[CTR Threshold Avoidance]] — threshold-calibrated structuring
- [[Placement Stage]] — structuring most often appears at placement

```adl:relation
source: "Structuring Typology"
relation: specialisation-of
target: "adl://public/concepts/money_laundering_placement"
mapping_type: ontological
confidence: 0.88
```

```adl:relation
source: "Structuring Typology"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-ctr-avoid"
mapping_type: statistical
confidence: 0.90
```

```adl:evidence
evidence_type: cross_reference
data_ref: regulatory://fatf/rec16_structuring
description: "FATF Recommendation 16 structuring guidance"
confidence: 0.89
observed_at: "2025-01-01T00:00:00Z"
```
