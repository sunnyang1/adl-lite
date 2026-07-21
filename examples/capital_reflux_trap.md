---
adl_type: discovery
adl_id: disc-capital-trap
status: provisional
confidence: 0.84
novelty: 0.91
domain: financial_aml
mechanism: isomorphic_mapping
scope: private/ceiec-aml
validators: []
provisional_names:
  zh: "资金注意力陷阱"
  en: "Capital Attention Trap"
evidence_refs:
  - vecdb://clusters/8912
  - tool://aml_simulator/v2
  - expert://aml_team/review_2024q2
---

# Capital Attention Trap

> Status: 🟡 provisional | Confidence: 84% | Novelty: 91%

## Discovery Statement

The AML transaction network exhibits an anomalous pattern where fund flows
concentrate on structurally peripheral nodes, creating "attention traps" which
camouflage illicit capital reflux.

## Intuition

Legitimate capital flows tend to concentrate on hub nodes (high betweenness).
In the observed AML network, illicit flows deliberately route through
peripheral nodes with high clustering coefficient, creating a topological
illusion of dispersion while actually funneling toward a common sink.

The capital trap pattern is **isomorphic** to the "gradient explosion" problem in deep learning:
- Gradient explosion: small weights amplify errors through multiplicative paths
- Capital trap: peripheral nodes amplify obscurity through structural camouflage

## Observation

In the monitored AML transaction network, fund flows concentrate on
structurally peripheral nodes instead of legitimate hub nodes. High-dimensional
clustering isolates the peripheral-node flows as 3-sigma outliers (E1), and
Monte Carlo simulation shows the "attention trap" topology forming under 78% of
adversarial routing strategies (E2). Senior analyst review against 5-year
historical data confirms the pattern is novel rather than a known layering
variant (E3).

## Reasoning

Illicit actors route capital through peripheral nodes with high clustering
coefficient, manufacturing a topological illusion of dispersion while funds
actually funnel toward a common sink. The mechanism is isomorphic to gradient
explosion in deep networks: just as small weights amplify error signals along
multiplicative paths, peripheral nodes amplify obscurity through structural
camouflage. The mapping preserves cycles, so graph-theoretic results from the
source domain transfer to the AML setting (see Formal Seal).

## Conclusion

The "Capital Attention Trap" is a distinct, previously unrecorded laundering
topology: an isomorphic mapping of gradient-explosion dynamics onto
transaction graphs, specialised from classical money-laundering layering.
Recommended actions: register as provisional discovery (confidence 84%),
request cross-agent validation via `adl://shared/ceiec-review`, and complete
the Lean 4 formal seal for cycle preservation.

## Related Concepts

- [[Gradient Explosion]] — public domain concept, topologically isomorphic source
- [[Money Laundering Layering]] — traditional AML technique
- [[Structural Hole Theory]] — Ron Burt's social network theory

```adl:relation
source: "Capital Attention Trap"
relation: isomorphic-to
target: "adl://public/concepts/gradient_explosion"
mapping_type: topological
confidence: 0.91
```

```adl:relation
source: "Capital Attention Trap"
relation: specialisation-of
target: "adl://public/concepts/money_laundering_layering"
mapping_type: ontological
confidence: 0.73
```

## Evidence Chain

### E1: Vector Clustering

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://clusters/8912
description: "High-dimensional clustering reveals 3-sigma outliers in peripheral-node transaction flows"
confidence: 0.87
observed_at: "2024-03-15T09:23:00Z"
```

### E2: Simulator Run

```adl:evidence
evidence_type: simulator_run
data_ref: tool://aml_simulator/v2
description: "Monte Carlo simulation confirms trap formation under 78% of adversarial routing strategies"
confidence: 0.82
observed_at: "2024-04-02T14:11:00Z"
```

### E3: Expert Review

```adl:evidence
evidence_type: human_expert
data_ref: expert://aml_team/review_2024q2
description: "Senior AML analyst confirmed pattern novelty against 5-year historical data"
confidence: 0.91
observed_at: "2024-05-10T11:00:00Z"
```

## Formal Seal

```adl:seal
assertion: "isomorphic_mapping_preserves_cycles"
language: lean4
proof_ref: "https://github.com/ceiec-aml/formal-proofs/isomorphism_cycles.lean"
status: pending
verified_by: null
```

## Consensus History

| Timestamp | Actor | Transition | Reason |
|-----------|-------|------------|--------|
| 2024-05-23 | agent_discovery | 🟡 provisional | Initial discovery |

---

*ADL Lite Document — Private/CEIEC-AML Scope*
*For cross-agent consensus, submit validation request to `adl://shared/ceiec-review`*
