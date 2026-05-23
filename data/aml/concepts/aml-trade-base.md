---
adl_type: concept
adl_id: aml-trade-base
status: validated
confidence: 0.78
novelty: 0.20
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "贸易洗钱"
  en: "Trade-Based Laundering"
evidence_refs:
  - vecdb://aml/aml_trade_base
  - fatf://typologies/tbml_2024
---

# Trade-Based Laundering

> Status: 🟢 validated | Confidence: 78%

## Definition

**Trade-Based Laundering (TBML)** moves value across borders by misrepresenting goods,
services, or their prices. TBML is the parent typology for invoice fraud, phantom shipments,
and commodity over/under valuation schemes.

## Monitoring Signals

- Price vs commodity index deviation sustained over multiple shipments
- Repeated HS-code changes for same counter-party pair
- Payment without matching logistics events in trade finance messages
- Free-trade zone entities with disproportionate global trade share

## Related Concepts

- [[Trade Misinvoicing]] — price manipulation specialisation
- [[Circular Trade Loop]] — closed commodity invoice cycles

```adl:relation
source: "Trade-Based Laundering"
relation: related-to
target: "adl://public/concepts/trade_based_money_laundering"
mapping_type: ontological
confidence: 0.90
```

```adl:relation
source: "Trade-Based Laundering"
relation: indexed-phrase
target: "s6b1tf52doc"
mapping_type: lexical
confidence: 0.90
```

```adl:evidence
evidence_type: cross_reference
data_ref: fatf://typologies/tbml_2024
description: "FATF TBML 2024 typology document mapping"
confidence: 0.91
observed_at: "2024-12-01T00:00:00Z"
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_trade_base
description: "Trade finance message graph without logistics anchor events"
confidence: 0.76
observed_at: "2026-02-05T09:00:00Z"
```
