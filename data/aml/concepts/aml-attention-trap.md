---
adl_type: concept
adl_id: aml-attention-trap
status: validated
confidence: 0.88
novelty: 0.72
domain: financial_aml
mechanism: isomorphic_mapping
scope: private/ceiec-aml
provisional_names:
  zh: "外围注意力陷阱"
  en: "Peripheral Attention Trap"
evidence_refs:
  - vecdb://aml/aml_attention_trap
  - tool://aml_simulator/v2
  - expert://aml_team/peripheral_review_2024q2
---

# Peripheral Attention Trap

> Status: 🟢 validated | Confidence: 88%

## Definition

The **Peripheral Attention Trap** names a graph-structural laundering signal: transaction
volume and alert density concentrate on low-betweenness peripheral accounts while
value consolidates toward a hidden sink. Monitoring systems overweight peripheral
noise and under-weight the consolidating corridor.

## Monitoring Signals

| Signal | Threshold heuristic | Interpretation |
|--------|---------------------|----------------|
| Peripheral clustering coefficient | Top decile vs sector baseline | Artificial dispersion |
| Hub bypass ratio | >0.6 of outbound value skips top-3 neighbors | Layering camouflage |
| Alert-to-value ratio | Peripheral alerts 3× hub alerts | Attention misallocation |
| Sink convergence | ≥2 hops to common beneficiary | Reflux endpoint |

## Operational Intuition

Legitimate retail flows anchor on high-betweenness hubs (payroll, marketplace settlement).
Illicit architects route through leaf-like accounts so investigators chase many low-value
alerts instead of one high-value corridor. The trap is **topologically isomorphic** to
gradient explosion: many small peripheral activations amplify obscurity along a deep path.

## Related Concepts

- [[Capital Attention Trap]] — formal discovery record for the same phenomenon
- [[Layering Chain]] — often co-occurs as the multi-hop path into peripherals
- [[Money Mule Account]] — peripheral accounts frequently operate as mules
- [[Gradient Explosion]] — public isomorphic source domain

```adl:relation
source: "Peripheral Attention Trap"
relation: specialisation-of
target: "adl://private/ceiec-aml/disc-capital-trap"
mapping_type: ontological
confidence: 0.92
```

```adl:relation
source: "Peripheral Attention Trap"
relation: isomorphic-to
target: "adl://public/concepts/gradient_explosion"
mapping_type: topological
confidence: 0.89
```

```adl:relation
source: "Peripheral Attention Trap"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-layering"
mapping_type: statistical
confidence: 0.81
```

## Evidence

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_attention_trap
description: "Graph embedding cluster #8912 — peripheral concentration with sink convergence"
confidence: 0.87
observed_at: "2024-03-15T09:23:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: tool://aml_simulator/v2
description: "Adversarial routing reproduces trap under 78% of Monte Carlo seeds"
confidence: 0.82
observed_at: "2024-04-02T14:11:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: expert://aml_team/peripheral_review_2024q2
description: "AML graph analytics lead confirmed pattern against 5-year retail network baseline"
confidence: 0.91
observed_at: "2024-05-10T11:00:00Z"
```
