---
adl_type: discovery
adl_id: disc-llm-crypto-mixer
status: provisional
confidence: 0.78
novelty: 0.65
domain: financial_aml
mechanism: compositional_blend
scope: private/ceiec-aml
provisional_names:
  en: "Crypto Mixer Exposure"
evidence_refs:
  - vecdb://ceiec-aml/tx-graph/2026-q2-mixer-clusters
---

# Crypto Mixer Exposure

## Discovery Statement

A compositional blend of mixer contract interaction patterns and peel-chain off-ramp structures yields a composite risk signal for crypto mixer exposure. The blend fuses two distinct on-chain behaviors — direct deposit into known mixer smart contracts (e.g., Tornado Cash, Railgun) and subsequent multi-hop peel-chain withdrawals that fragment funds across fresh wallets before fiat off-ramp — into a single exposure metric. When both pattern families co-occur within a configurable time window and share a common funding origin, the combined signal exceeds the risk contribution of either pattern in isolation, enabling more precise prioritization of suspicious transaction reports in anti-money laundering workflows.

## Intuition

The core insight draws from the observation that sophisticated obfuscation actors rarely rely on a single technique. Mixer contract deposits provide the initial layer of on-chain anonymity, while peel-chain off-ramp structures convert mixed outputs into fiat currency through a cascade of diminishing transfers. Individually, each pattern carries moderate risk weight. The compositional blend recognizes that the conjunction of mixer deposit followed by peel-chain off-ramp within a bounded temporal window constitutes a qualitatively different risk archetype — one where the two mechanisms reinforce each other. The blend operator assigns a multiplicative rather than additive risk coefficient when both pattern families are detected on the same entity graph, reflecting the elevated intent to evade traceability.

## Related Concepts

- [[AML Crypto Mix]] — foundational concept covering mixer contract mechanics and peel-chain off-ramp structures
- [[Peel Chain Detection]] — pattern recognition for multi-hop fund fragmentation
- [[On-Chain Entity Clustering]] — wallet grouping methodology that feeds exposure scoring

```adl:relation
source: "Crypto Mixer Exposure"
relation: compositional-blend-of
target: "adl://public/concepts/aml-crypto-mix"
mapping_type: compositional
confidence: 0.82
```

```adl:relation
source: "Crypto Mixer Exposure"
relation: depends-on
target: "adl://public/concepts/peel-chain-detection"
mapping_type: functional
confidence: 0.75
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/tx-graph/2026-q2-mixer-clusters
description: "Cluster analysis of 4,217 wallet entities exhibiting both mixer contract deposit and peel-chain off-ramp patterns within a 72-hour window. Composite exposure score distribution shows a distinct bimodal separation from single-pattern entities, with mean composite risk 2.3x the additive baseline."
confidence: 0.78
observed_at: "2026-05-23T00:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: vecdb://ceiec-aml/expert-review/2026-q2-mixer-blend
description: "Senior AML analyst review of 150 flagged composite exposure cases confirmed 89% true-positive rate for illicit fund movement, compared to 62% true-positive rate for mixer-only flags and 54% for peel-chain-only flags in the same cohort."
confidence: 0.85
observed_at: "2026-05-20T00:00:00Z"
```