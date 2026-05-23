---
adl_type: concept
adl_id: aml-rapid-move
status: validated
confidence: 0.83
novelty: 0.38
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "极速跨境流转"
  en: "Rapid Movement"
evidence_refs:
  - vecdb://aml/aml_rapid_move
  - swift://velocity/corridor_stats
---

# Rapid Movement

> Status: 🟢 validated | Confidence: 83%

## Definition

**Rapid Movement** detects funds crossing multiple jurisdictions within hours, exceeding
velocity norms for the customer segment and corridor. Legitimate trade finance can be fast;
Rapid Movement flags absence of documentary trade support or repeated use of high-risk corridors.

## Monitoring Signals

- ≥3 country hops within 12 hours on retail-tier account
- Velocity z-score >3 vs 90-day customer baseline
- Same-day in-out with <1% retained balance (pass-through)
- Correspondent chain compression under 4 hours end-to-end

## Related Concepts

- [[Informal Value Transfer]] — hawala-like speed without SWIFT trail
- [[Layering Chain]] — velocity layered across hops
- [[Round Trip Transfer]] — rapid return leg to origin jurisdiction

```adl:relation
source: "Rapid Movement"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-hawala"
mapping_type: statistical
confidence: 0.70
```

```adl:evidence
evidence_type: empirical_observation
data_ref: swift://velocity/corridor_stats
description: "Corridor velocity benchmark breach on retail SWIFT messages"
confidence: 0.85
observed_at: "2026-02-28T00:00:00Z"
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_rapid_move
description: "Temporal graph feature — cross-border hop count / elapsed time ratio"
confidence: 0.81
observed_at: "2026-03-22T08:00:00Z"
```
