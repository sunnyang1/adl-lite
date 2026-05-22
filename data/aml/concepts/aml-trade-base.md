---
adl_type: concept
adl_id: aml-trade-base
status: validated
confidence: 0.75
novelty: 0.35
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  en: "Trade-Based ML"
evidence_refs:
  - vecdb://aml/aml_trade_base
---

# Trade-Based ML

## Definition

Commodity invoice manipulation in anti-money laundering monitoring contexts.

## Related Concepts

- [[Capital Attention Trap]] — cross-domain structural analogy

```adl:relation
source: "Trade-Based ML"
relation: related-to
target: "adl://private/ceiec-aml/disc-capital-trap"
mapping_type: domain
confidence: 0.70
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_trade_base
description: "AML feature cluster for trade-based ml"
confidence: 0.72
observed_at: "2026-05-01T00:00:00Z"
```
