---
adl_type: discovery
adl_id: disc-llm-peripheral-trap-batch001
status: provisional
confidence: 0.72
novelty: 0.65
domain: financial_aml
mechanism: isomorphic_mapping
scope: private/ceiec-aml
provisional_names:
  en: "Peripheral Attention Trap"
  zh: "外围注意力陷阱"
evidence_refs:
  - vecdb://ceiec-aml/peripheral_trap-batch001-2026q2
  - tool://aml_simulator/v2/peripheral-trap-batch001
---

# Peripheral Attention Trap

## Discovery Statement

AML transaction graphs show alert-to-value ratio skews toward low-centrality feeders before sink convergence. The Peripheral Attention Trap names adversarial routing that parks volume on low-betweenness accounts so monitoring attention decays with hop distance from flagged subjects. Sink convergence toward dormant beneficiary wallets confirms the trap: multiple peripheral chains terminate at shared extraction endpoints invisible to hub-centric heuristics.

## Intuition

Graph monitoring stacks rank nodes by proximity to open investigations. Layering teams add benign-looking intermediaries until attention scores on terminal beneficiaries fall below operational review thresholds. Peripheral Attention Trap documentation ties the evasion geometry to aml-attention-trap monitoring signals: peripheral clustering, hub bypass, alert-to-value imbalance, and sink convergence within two hops.

## Related Concepts

- [[Peripheral Attention Trap]] — discovery anchor for RQ1 batch 001
- [[AML monitoring graph]] — transaction graph subject to attention-weighted review
- [[Sink convergence]] — shared beneficiary aggregation after peripheral routing

```adl:relation
source: "Peripheral Attention Trap"
relation: isomorphic-to
target: "adl://public/concepts/aml-attention-trap"
mapping_type: topological
confidence: 0.86
```

```adl:relation
source: "Peripheral Attention Trap"
relation: analogical-to
target: "adl://public/concepts/gradient_explosion"
mapping_type: structural
confidence: 0.74
```

```adl:relation
source: "Peripheral Attention Trap"
relation: specialisation-of
target: "adl://public/concepts/aml-attention-trap"
mapping_type: ontological
confidence: 0.71
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/peripheral_trap-batch001-2026q2
description: "Vector clustering over -batch001 cohort surfaces coordinated peripheral or mixer-linked behavior aligned with data/aml/concepts/aml-attention-trap.md heuristics."
confidence: 0.79
observed_at: "2026-05-24T00:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: tool://aml_simulator/v2/peripheral-trap-batch001
description: "Monte Carlo laundering simulation replays adversarial routing strategies; evasion success correlates with attention decay or sub-threshold structuring parameters from the concept stub."
confidence: 0.73
observed_at: "2026-05-24T00:00:00Z"
```
