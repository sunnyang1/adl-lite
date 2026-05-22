---
adl_type: concept
adl_id: aml-layering
status: validated
confidence: 0.75
novelty: 0.35
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  en: "Layering Chain"
evidence_refs:
  - vecdb://aml/aml_layering
---

# Layering Chain

## Definition

Multi-hop obfuscation of fund origin in anti-money laundering monitoring contexts.

## Related Concepts

- [[Capital Attention Trap]] — cross-domain structural analogy

```adl:relation
source: "Layering Chain"
relation: related-to
target: "adl://private/ceiec-aml/disc-capital-trap"
mapping_type: domain
confidence: 0.70
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_layering
description: "AML feature cluster for layering chain"
confidence: 0.72
observed_at: "2026-05-01T00:00:00Z"
```
