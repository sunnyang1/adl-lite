---
adl_type: discovery
adl_id: disc-llm-crypto-mixer-batch003
status: provisional
confidence: 0.76
novelty: 0.71
domain: financial_aml
mechanism: compositional_blend
scope: private/ceiec-aml
provisional_names:
  en: "Crypto Mixer Exposure"
  zh: "加密货币混币器暴露"
evidence_refs:
  - vecdb://ceiec-aml/crypto_mixer-batch003-2026q2
  - tool://aml_simulator/v2/crypto-mixer-batch003
---

# Crypto Mixer Exposure

## Discovery Statement

On-chain surveillance flags inbound transfers from labeled tumbler contracts spike before peel-chain exits. Crypto Mixer Exposure documents how tumbler deposits, peel chains, and fiat off-ramps compose a laundering stack where each leg alone appears plausibly legitimate until linked through shared timing and amount bands.

## Intuition

Mixer contracts break address lineage while peel chains reintroduce spendable UTXOs at exchange deposit addresses. Crypto Mixer Exposure ties wallet-level signals to aml-crypto-mix monitoring: mixer contract labels, peel-chain depth, and stablecoin off-ramp velocity relative to historical wallet behavior.

## Related Concepts

- [[Crypto Mixer Exposure]] — discovery anchor for RQ1 batch 003
- [[AML monitoring graph]] — transaction graph subject to attention-weighted review
- [[Sink convergence]] — shared beneficiary aggregation after peripheral routing

```adl:relation
source: "Crypto Mixer Exposure"
relation: isomorphic-to
target: "adl://public/concepts/aml-crypto-mix"
mapping_type: topological
confidence: 0.86
```

```adl:relation
source: "Crypto Mixer Exposure"
relation: related-to
target: "adl://public/concepts/peel_chain_laundering"
mapping_type: domain
confidence: 0.74
```

```adl:relation
source: "Crypto Mixer Exposure"
relation: specialisation-of
target: "adl://public/concepts/aml-crypto-mix"
mapping_type: ontological
confidence: 0.71
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://ceiec-aml/crypto_mixer-batch003-2026q2
description: "Vector clustering over -batch003 cohort surfaces coordinated peripheral or mixer-linked behavior aligned with data/aml/concepts/aml-crypto-mix.md heuristics."
confidence: 0.79
observed_at: "2026-05-24T00:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: tool://aml_simulator/v2/crypto-mixer-batch003
description: "Monte Carlo laundering simulation replays adversarial routing strategies; evasion success correlates with attention decay or sub-threshold structuring parameters from the concept stub."
confidence: 0.73
observed_at: "2026-05-24T00:00:00Z"
```
