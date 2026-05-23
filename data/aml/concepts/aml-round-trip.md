---
adl_type: concept
adl_id: aml-round-trip
status: validated
confidence: 0.81
novelty: 0.35
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "资金回流"
  en: "Round Trip Transfer"
evidence_refs:
  - vecdb://aml/aml_round_trip
---

# Round Trip Transfer

> Status: 🟢 validated | Confidence: 81%

## Definition

A **Round Trip Transfer** sends funds abroad and re-imports them to the same beneficial
network within a short window, often via different entity names or instruments. The pattern
simulates foreign investment or trade while preserving domestic control and obscuring origin.

## Monitoring Signals

- Outbound wire matched by inbound from related party within 7 days (±2% amount)
- Different entity names sharing UBO graph on both legs
- No customs or shipping record for claimed trade purpose
- FX gain/loss inconsistent with corridor spread

## Related Concepts

- [[Rapid Movement]] — compressed timing between legs
- [[Trade Misinvoicing]] — trade pretense for round trips
- [[Layering Chain]] — intermediate hops before return

```adl:relation
source: "Round Trip Transfer"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-rapid-move"
mapping_type: statistical
confidence: 0.72
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_round_trip
description: "Closed loop detection on entity graph with amount symmetry score >0.95"
confidence: 0.83
observed_at: "2025-10-30T09:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: tool://aml_simulator/v2
description: "Round-trip seed replay — 81% recall at 7-day window"
confidence: 0.78
observed_at: "2026-01-15T14:00:00Z"
```
