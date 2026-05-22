---
adl_type: concept
adl_id: aml-mule-acct
status: validated
confidence: 0.75
novelty: 0.35
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  en: "Money Mule Account"
evidence_refs:
  - vecdb://aml/aml_mule_acct
---

# Money Mule Account

## Definition

Third-party account used as pass-through in anti-money laundering monitoring contexts.

## Related Concepts

- [[Capital Attention Trap]] — cross-domain structural analogy

```adl:relation
source: "Money Mule Account"
relation: related-to
target: "adl://private/ceiec-aml/disc-capital-trap"
mapping_type: domain
confidence: 0.70
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_mule_acct
description: "AML feature cluster for money mule account"
confidence: 0.72
observed_at: "2026-05-01T00:00:00Z"
```
