---
adl_type: concept
adl_id: aml-real-estate
status: validated
confidence: 0.80
novelty: 0.29
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "房地产洗钱"
  en: "Real Estate Laundering"
evidence_refs:
  - vecdb://aml/aml_real_estate
---

# Real Estate Laundering

> Status: 🟢 validated | Confidence: 80%

## Definition

**Real Estate Laundering** parks illicit value in property purchases, renovations, or
flips with opaque ownership structures. High-value all-cash purchases, rapid resale, and
third-party payers on behalf of undisclosed UBOs are primary monitoring anchors.

## Monitoring Signals

- All-cash purchase >$1M by newly formed LLC without mortgage history
- Resale within 12 months at ±5% price (wash trade appearance)
- Renovation invoices from related-party contractors inflating basis
- Property income inconsistent with rental market comparables

## Related Concepts

- [[Beneficial Owner Gap]] — LLC and trust ownership opacity
- [[PEP Association]] — PEP proceeds often integrate via property
- [[Shell Company Network]] — purchasing entities

```adl:relation
source: "Real Estate Laundering"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-ben-owner"
mapping_type: statistical
confidence: 0.78
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_real_estate
description: "Property transaction graph — cash buyer LLC age vs price percentile"
confidence: 0.81
observed_at: "2025-08-30T10:00:00Z"
```

```adl:evidence
evidence_type: empirical_observation
data_ref: expert://aml_team/property_typology_2025
description: "Regional property AML typology sheet — all-cash LLC purchases"
confidence: 0.85
observed_at: "2025-10-01T00:00:00Z"
```
