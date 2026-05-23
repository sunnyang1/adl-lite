---
adl_type: concept
adl_id: aml-trade-mis
status: validated
confidence: 0.81
novelty: 0.32
domain: financial_aml
mechanism: analogical_transfer
scope: private/ceiec-aml
provisional_names:
  zh: "贸易虚开发票"
  en: "Trade Misinvoicing"
evidence_refs:
  - vecdb://aml/aml_trade_mis
  - customs://manifest/price_anomaly
---

# Trade Misinvoicing

> Status: 🟢 validated | Confidence: 81%

## Definition

**Trade Misinvoicing** manipulates import/export declared values to move value across
borders without corresponding goods flow. Over-invoicing shifts capital outward;
under-invoicing pulls capital inward while evading duties and AML scrutiny on true price.

## Monitoring Signals

- Unit price deviation >2σ from HS-code benchmark for corridor
- Quantity/weight inconsistent with commodity norms
- Repeated trading with shell counterparties in free-trade zones
- Payment timing decoupled from bill of lading by >30 days

## Related Concepts

- [[Trade-Based Laundering]] — parent typology
- [[Circular Trade Loop]] — closed invoice cycles
- [[Shell Company Network]] — counter-party structures

```adl:relation
source: "Trade Misinvoicing"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-trade-base"
mapping_type: ontological
confidence: 0.90
```

```adl:relation
source: "Trade Misinvoicing"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-shell-co"
mapping_type: statistical
confidence: 0.74
```

```adl:evidence
evidence_type: empirical_observation
data_ref: customs://manifest/price_anomaly
description: "Customs price benchmark outliers linked to flagged trade corridors"
confidence: 0.83
observed_at: "2025-08-01T00:00:00Z"
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_trade_mis
description: "Invoice-payment graph with HS-code price z-score >2.5"
confidence: 0.79
observed_at: "2026-03-10T10:00:00Z"
```
