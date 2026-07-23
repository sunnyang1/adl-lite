---
adl_type: concept
adl_id: concept-gradient-explosion
status: validated
confidence: 0.95
novelty: 0.40
domain: deep_learning
scope: public
provisional_names:
  zh: "梯度爆炸"
  en: "Gradient Explosion"
evidence_refs:
  - file://papers/bengio1994_gradient_issues
---

# Gradient Explosion

## Definition

Gradient explosion occurs when backpropagated gradients grow exponentially
across layers, destabilizing optimization and producing NaN weights in deep
networks.

## Observation

In deep recurrent and feed-forward networks, per-layer gradient norms are
empirically observed to multiply across depth: gradients that start near unit
scale at the output layer reach magnitudes that overflow floating-point
representation within tens of layers, producing NaN weights and abrupt loss
divergence (Bengio et al., 1994).

## Reasoning

Backpropagation composes per-layer Jacobian matrices; when the spectral
radius of the product exceeds one, each additional layer multiplies the
gradient magnitude instead of shrinking the gradient. Because the effect compounds
multiplicatively with depth, even mild per-layer amplification becomes an
exponential blow-up in deep stacks.

## Conclusion

Gradient explosion is a multiplicative, depth-driven failure mode of deep
optimization. Standard mitigations are gradient clipping, residual
connections, careful initialization, and normalization layers; the concept
is the dual failure mode of the vanishing gradient and is tracked here as a
validated public concept.

## Related Concepts

- [[Vanishing Gradient]] — complementary failure mode in deep networks
- [[Residual Connection]] — architectural mitigation

```adl:relation
source: "Gradient Explosion"
relation: dual-of
target: "adl://public/concepts/vanishing_gradient"
mapping_type: ontological
confidence: 0.88
```

```adl:evidence
evidence_type: cross_reference
data_ref: file://papers/bengio1994_gradient_issues
description: "Classic treatment of recurrent and deep net gradient pathology"
confidence: 0.92
observed_at: "1994-01-01T00:00:00Z"
```

---

*ADL Lite Document — Public scope*
