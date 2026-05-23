---
adl_type: concept
adl_id: aml-trade-loop
status: validated
confidence: 0.80
novelty: 0.37
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "循环贸易圈"
  en: "Circular Trade Loop"
evidence_refs:
  - vecdb://aml/aml_trade_loop
---

# Circular Trade Loop

> Status: 🟢 validated | Confidence: 80%

## Definition

A **Circular Trade Loop** is a closed cycle of invoices and payments among related entities
without net economic output. Goods may not move; documents circulate to justify repeated
cross-border settlements and inflate trade statistics.

## Monitoring Signals

- Strongly connected component in trade counter-party graph size ≥4
- Net commodity flow near zero across cycle members over 90 days
- Invoice amounts balanced to ±1% around ring (wash symmetry)
- Same logistics provider on all legs without cargo weight variance

## Related Concepts

- [[Trade Misinvoicing]] — pricing fraud within loops
- [[Trade-Based Laundering]] — parent typology
- [[Shell Company Network]] — loop members often shells

```adl:relation
source: "Circular Trade Loop"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-trade-mis"
mapping_type: ontological
confidence: 0.79
```

```adl:relation
source: "Circular Trade Loop"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-shell-co"
mapping_type: statistical
confidence: 0.76
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_trade_loop
description: "Trade graph SCC detection with near-zero net commodity flow"
confidence: 0.82
observed_at: "2025-11-28T12:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: tool://trade/graph_cycle_detector
description: "Cycle detector recall 0.86 on synthetic TBML ring seeds"
confidence: 0.77
observed_at: "2026-02-14T10:00:00Z"
```
