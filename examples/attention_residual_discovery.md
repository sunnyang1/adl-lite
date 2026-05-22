---
adl_type: discovery
adl_id: disc-attention-residual
status: provisional
confidence: 0.79
novelty: 0.86
domain: deep_learning
mechanism: analogical_transfer
scope: private/research-lab
provisional_names:
  zh: "注意力残差耦合"
  en: "Attention Residual Coupling"
evidence_refs:
  - vecdb://embeddings/attn_residual_v3
  - tool://transformer_probe/v1
---

# Attention Residual Coupling

> Status: 🟡 provisional | Confidence: 79% | Novelty: 86%

## Discovery Statement

Transformer blocks exhibit coupled dynamics between attention logits and
residual stream norms: when residual norms spike, attention entropy collapses
on a narrow token subset, amplifying representation drift in later layers.

## Intuition

The coupling mirrors peripheral-node concentration in financial flow graphs:
local amplification in one channel (residual norm) forces global re-routing
(attention mass) toward a few hubs.

## Related Concepts

- [[Gradient Explosion]] — public reference for multiplicative amplification
- [[Layer Normalization]] — common stabilizer

```adl:relation
source: "Attention Residual Coupling"
relation: analogical-to
target: "adl://public/concepts/gradient_explosion"
mapping_type: structural
confidence: 0.81
```

```adl:relation
source: "Attention Residual Coupling"
relation: mitigated-by
target: "adl://public/concepts/layer_normalization"
mapping_type: engineering
confidence: 0.74
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://embeddings/attn_residual_v3
description: "Embedding cluster shows co-movement of attn entropy and residual L2"
confidence: 0.80
observed_at: "2026-05-20T10:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: tool://transformer_probe/v1
description: "Synthetic 12-layer transformer reproduces coupling under 68% of init seeds"
confidence: 0.77
observed_at: "2026-05-21T14:30:00Z"
```

---

*ADL Lite Document — Private/research-lab scope*
