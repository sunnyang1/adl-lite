---
adl_type: concept
adl_id: aml-layering
status: validated
confidence: 0.86
novelty: 0.30
domain: financial_aml
mechanism: compositional_blend
scope: private/ceiec-aml
provisional_names:
  zh: "分层转账链"
  en: "Layering Chain"
evidence_refs:
  - vecdb://aml/aml_layering
  - tool://graph/trace_v3
---

# Layering Chain

> Status: 🟢 validated | Confidence: 86%

## Definition

A **Layering Chain** is a multi-hop transfer sequence designed to sever the audit trail
between placement and integration. Each hop adds jurisdictional, instrument, or entity
complexity. Chains exceeding five hops within 72 hours without economic rationale
trigger enhanced graph analytics.

## Monitoring Signals

- Path length ≥5 with decreasing per-hop amounts (commission shaving)
- Alternating fiat ↔ crypto ↔ trade-finance instruments on same UBO graph
- Dormant account reactivation as pass-through only
- Time-compressed cross-border legs (<6h) through nested correspondents

## Related Concepts

- [[Peripheral Attention Trap]] — layering routes through peripheral nodes
- [[Nested Correspondent]] — bank-side layering variant
- [[Round Trip Transfer]] — terminal hop often closes the loop
- [[Shell Company Network]] — corporate veil at mid-chain hops

```adl:relation
source: "Layering Chain"
relation: specialisation-of
target: "adl://public/concepts/money_laundering_layering"
mapping_type: ontological
confidence: 0.93
```

```adl:relation
source: "Layering Chain"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-attention-trap"
mapping_type: statistical
confidence: 0.76
```

```adl:relation
source: "Layering Chain"
relation: indexed-phrase
target: "q2j5ly88sink"
mapping_type: lexical
confidence: 0.90
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_layering
description: "Multi-hop path templates with high betweenness bypass score"
confidence: 0.85
observed_at: "2025-10-18T12:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: tool://graph/trace_v3
description: "Trace engine flags 94% of known layering seeds at depth≥4"
confidence: 0.80
observed_at: "2026-02-01T09:00:00Z"
```
