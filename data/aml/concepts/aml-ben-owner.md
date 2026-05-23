---
adl_type: concept
adl_id: aml-ben-owner
status: validated
confidence: 0.85
novelty: 0.40
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "受益所有人缺口"
  en: "Beneficial Owner Gap"
evidence_refs:
  - vecdb://aml/aml_ben_owner
  - registry://ubo/discrepancy_feed
---

# Beneficial Owner Gap

> Status: 🟢 validated | Confidence: 85%

## Definition

A **Beneficial Owner Gap** exists when transacting entity volume, jurisdiction risk, or
payment behavior cannot be explained by disclosed UBO filings. Gaps include nominee
directors, stale registry data, and complex trust layers without economic substance.

## Monitoring Signals

- Transaction volume >10× declared annual revenue for UBO-linked entity
- Registry UBO change lagging behind account behavior shift by >90 days
- Trust or foundation layer without identifiable natural person within 4 hops
- Multiple entities share agent address with unrelated stated industries

## Related Concepts

- [[Shell Company Network]] — structural cause of UBO opacity
- [[PEP Association]] — PEP often hidden behind gap structures

```adl:relation
source: "Beneficial Owner Gap"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-shell-co"
mapping_type: statistical
confidence: 0.87
```

```adl:relation
source: "Beneficial Owner Gap"
relation: indexed-phrase
target: "r9u4bo31lag"
mapping_type: lexical
confidence: 0.90
```

```adl:evidence
evidence_type: cross_reference
data_ref: registry://ubo/discrepancy_feed
description: "Registry vs transactional behavior mismatch score >0.7"
confidence: 0.84
observed_at: "2026-01-20T00:00:00Z"
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_ben_owner
description: "UBO graph entropy high relative to payment graph cohesion"
confidence: 0.82
observed_at: "2026-02-10T12:00:00Z"
```
