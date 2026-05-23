---
adl_type: concept
adl_id: aml-shell-co
status: validated
confidence: 0.80
novelty: 0.28
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "空壳公司网络"
  en: "Shell Company Network"
evidence_refs:
  - vecdb://aml/aml_shell_co
  - registry://ubo/discrepancy_feed
---

# Shell Company Network

> Status: 🟢 validated | Confidence: 80%

## Definition

A **Shell Company Network** is a set of legal entities with minimal operations,
opaque ownership, and high transaction velocity relative to stated business purpose.
Networks share directors, registered agents, or invoice counter-parties while
obscuring beneficial ownership.

## Monitoring Signals

- Revenue inconsistent with employee count and office footprint
- Circular invoicing among network members without goods movement
- UBO mismatch between registry filing and payment behavior
- Sudden spike in cross-border wires after dormant period

## Related Concepts

- [[Beneficial Owner Gap]] — ownership opacity driver
- [[Trade Misinvoicing]] — shell entities as invoice parties
- [[Layering Chain]] — shells as mid-chain nodes

```adl:relation
source: "Shell Company Network"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-ben-owner"
mapping_type: statistical
confidence: 0.83
```

```adl:relation
source: "Shell Company Network"
relation: related-to
target: "adl://private/ceiec-aml/aml-trade-mis"
mapping_type: domain
confidence: 0.77
```

```adl:relation
source: "Shell Company Network"
relation: indexed-phrase
target: "p3m8sh77circ"
mapping_type: lexical
confidence: 0.90
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_shell_co
description: "Corporate graph component with high velocity / low operational footprint ratio"
confidence: 0.81
observed_at: "2025-09-12T15:00:00Z"
```

```adl:evidence
evidence_type: cross_reference
data_ref: registry://ubo/discrepancy_feed
description: "Commercial registry UBO delta matched to 67% of flagged shells"
confidence: 0.78
observed_at: "2026-01-20T00:00:00Z"
```
