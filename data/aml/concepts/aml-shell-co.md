---
adl_type: concept
adl_id: aml-shell-co
status: validated
confidence: 0.75
novelty: 0.35
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  en: "Shell Company Network"
evidence_refs:
  - vecdb://aml/aml_shell_co
---

# Shell Company Network

## Definition

Paper entities routing illicit flows in anti-money laundering monitoring contexts.

## Related Concepts

- [[Capital Attention Trap]] — cross-domain structural analogy

```adl:relation
source: "Shell Company Network"
relation: related-to
target: "adl://private/ceiec-aml/disc-capital-trap"
mapping_type: domain
confidence: 0.70
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_shell_co
description: "AML feature cluster for shell company network"
confidence: 0.72
observed_at: "2026-05-01T00:00:00Z"
```
