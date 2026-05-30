---
adl_type: discovery
adl_id: disc-llm-smurfing-pattern-batch008
status: provisional
confidence: 0.76
novelty: 0.62
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  en: "Smurfing Pattern"
  zh: "拆分存款模式"
evidence_refs:
  - vecdb://ceiec-aml/smurfing_pattern-batch008-2026q2
  - tool://aml_simulator/v2/smurfing-pattern-batch008
---

# Smurfing Pattern

## Discovery Statement

Beneficial-owner networks exhibit round-dollar deposit bursts precede twenty-four-hour consolidation wires. The Smurfing Pattern reconstructs placement volume above currency reporting limits by fanning structured deposits across many low-risk retail endpoints before a consolidation account absorbs the aggregate flow.

## Intuition

CTR heuristics treat each retail account independently while smurfing operators coordinate timing, amount bands, and channel choice. Smurfing Pattern discovery prose aligns with aml-smurfing concept thresholds and consolidation transfer monitoring so investigators can compare emergent fan-in graphs against typology baselines.

## Related Concepts

- [[Smurfing Pattern]] — discovery anchor for RQ1 batch 008
- [[AML monitoring graph]] — transaction graph subject to attention-weighted review
- [[Sink convergence]] — shared beneficiary aggregation after peripheral routing

```adl:relation
source: "Smurfing Pattern"
relation: isomorphic-to
target: "adl://public/concepts/aml-smurfing"
mapping_type: topological
confidence: 0.86
```

```adl:relation
source: "Smurfing Pattern"
relation: co-occurs-with
target: "adl://public/concepts/money_laundering_layering"
mapping_type: statistical
confidence: 0.74
```

```adl:relation
source: "Smurfing Pattern"
relation: specialisation-of
target: "adl://public/concepts/aml-smurfing"
mapping_type: ontological
confidence: 0.71
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/smurfing_pattern-batch008-2026q2
description: "Vector clustering over -batch008 cohort surfaces coordinated peripheral or mixer-linked behavior aligned with data/aml/concepts/aml-smurfing.md heuristics."
confidence: 0.79
observed_at: "2026-05-24T00:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: tool://aml_simulator/v2/smurfing-pattern-batch008
description: "Monte Carlo laundering simulation replays adversarial routing strategies; evasion success correlates with attention decay or sub-threshold structuring parameters from the concept stub."
confidence: 0.73
observed_at: "2026-05-24T00:00:00Z"
```
