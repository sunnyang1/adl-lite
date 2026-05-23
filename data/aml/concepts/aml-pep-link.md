---
adl_type: concept
adl_id: aml-pep-link
status: validated
confidence: 0.79
novelty: 0.22
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "政治公众人物关联"
  en: "PEP Association"
evidence_refs:
  - vecdb://aml/aml_pep_link
  - watchlist://pep/global_2026
---

# PEP Association

> Status: 🟢 validated | Confidence: 79%

## Definition

**PEP Association** marks customers or counterparties within two relationship hops of a
Politically Exposed Person per internal watchlist policy. Association elevates due-diligence
tier and tightens transaction monitoring thresholds regardless of current adverse media status.

## Monitoring Signals

- Family or business partner graph edge to tier-1 PEP
- Sudden wealth inflow inconsistent with declared public-sector income
- Gifts or consulting fees from state-linked enterprises
- Geographic routing through PEP home jurisdiction without trade rationale

## Related Concepts

- [[Beneficial Owner Gap]] — PEP networks hide behind opaque UBO chains
- [[Real Estate Laundering]] — common integration asset class for PEP flows

```adl:relation
source: "PEP Association"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-ben-owner"
mapping_type: statistical
confidence: 0.75
```

```adl:evidence
evidence_type: cross_reference
data_ref: watchlist://pep/global_2026
description: "Global PEP watchlist graph match within 2-hop corporate network"
confidence: 0.92
observed_at: "2026-01-01T00:00:00Z"
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_pep_link
description: "Customer graph PEP proximity score above policy cutoff"
confidence: 0.77
observed_at: "2025-12-05T11:00:00Z"
```
