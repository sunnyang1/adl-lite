---
adl_type: discovery
adl_id: disc-matdo-kinetic
status: provisional
confidence: 0.68
novelty: 0.85
domain: materials_science
mechanism: compositional_blend
scope: private/materials-lab
provisional_names:
  zh: "矩阵域动力学成核"
  en: "Matrix Domain Kinetic Nucleation"
evidence_refs:
  - vecdb://materials/matdo_kinetic_17
  - expert://materials_team/review_2026q1
---

# Matrix Domain Kinetic Nucleation

> Status: 🟡 provisional | Confidence: 68% | Novelty: 85%

## Discovery Statement

The MATDO phenomenon is better explained by stochastic nucleation at defect
sites under thermal flux, not by global domain alignment. Ordering emerges
from local nucleation cascades rather than bulk gradient coupling.

## Intuition

Forked from `disc-matdo-original`: replaces global alignment with localized
nucleation events. Competing mechanism hypothesis pending merger review.

## Related Concepts

- [[Matrix Domain Ordering]] — original fork parent (deprecated interpretation)
- [[Nucleation Theory]] — classical materials framework

```adl:relation
source: "Matrix Domain Kinetic Nucleation"
relation: fork-of
target: "adl://private/materials-lab/disc-matdo-original"
mapping_type: ontological
confidence: 0.95
```

```adl:relation
source: "Matrix Domain Kinetic Nucleation"
relation: specialisation-of
target: "adl://public/concepts/nucleation_theory"
mapping_type: ontological
confidence: 0.82
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://materials/matdo_kinetic_17
description: "Defect-site nucleation rate predicts ordering onset better than gradient model"
confidence: 0.71
observed_at: "2026-05-01T09:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: expert://materials_team/review_2026q1
description: "Materials team rated kinetic hypothesis as plausible alternative"
confidence: 0.75
observed_at: "2026-05-05T14:00:00Z"
```

---

*ADL Lite Document — Fork of disc-matdo-original*
