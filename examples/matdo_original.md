---
adl_type: discovery
adl_id: disc-matdo-original
status: forked
confidence: 0.72
novelty: 0.88
domain: materials_science
mechanism: emergent_pattern
scope: private/materials-lab
provisional_names:
  zh: "矩阵域有序化"
  en: "Matrix Domain Ordering"
evidence_refs:
  - vecdb://materials/matdo_cluster_42
  - tool://xrd_simulator/v1
---

# Matrix Domain Ordering (MATDO)

> Status: 🔵 forked | Confidence: 72% | Novelty: 88%

## Discovery Statement

Polycrystalline alloy samples show spontaneous domain alignment when thermal
gradients exceed a critical threshold, producing measurable anisotropy in
X-ray diffraction without external field application.

## Intuition

Local grain boundary mobility couples with bulk thermal flux, creating a
self-organizing ordering front analogous to attention mass collapse in
transformer residual streams.

## Observation

X-ray diffraction measurements on polycrystalline alloy samples show peak
sharpening whose magnitude correlates with the applied thermal gradient,
and Monte Carlo grain-growth simulation reproduces spontaneous domain
ordering at 71% of seeds — with no external field applied in either setting.

## Reasoning

Above a critical thermal gradient, grain boundary mobility rises enough for
local energy minimization to propagate across neighboring grains. The
ordering front then self-organizes: each aligned domain lowers the barrier
for adjacent domains, so a bulk-scale anisotropy emerges from purely local
coupling — structurally analogous to attention mass collapsing onto hub
tokens in transformer residual streams.

## Conclusion

Matrix Domain Ordering is a candidate emergent mechanism for field-free
anisotropy in polycrystalline alloys. The original bulk-coupling
interpretation is contested by a kinetic nucleation fork
(`disc-matdo-kinetic`); the concept is marked forked pending merger review.

## Related Concepts

- [[Gradient Explosion]] — multiplicative amplification analogy
- [[Phase Transition]] — thermodynamic framing

```adl:relation
source: "Matrix Domain Ordering"
relation: analogical-to
target: "adl://public/concepts/gradient_explosion"
mapping_type: structural
confidence: 0.65
```

```adl:relation
source: "Matrix Domain Ordering"
relation: specialisation-of
target: "adl://public/concepts/phase_transition"
mapping_type: ontological
confidence: 0.78
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://materials/matdo_cluster_42
description: "XRD peak sharpening correlates with thermal gradient magnitude"
confidence: 0.74
observed_at: "2026-04-10T08:00:00Z"
```

```adl:evidence
evidence_type: simulator_run
data_ref: tool://xrd_simulator/v1
description: "Monte Carlo grain growth reproduces ordering at 71% of seeds"
confidence: 0.70
observed_at: "2026-04-15T12:00:00Z"
```

---

*ADL Lite Document — Private/materials-lab scope*
*Fork alternate: `disc-matdo-kinetic` (kinetic nucleation hypothesis)*
