---
adl_type: concept
adl_id: aml-nesting
status: validated
confidence: 0.79
novelty: 0.33
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "嵌套代理行"
  en: "Nested Correspondent"
evidence_refs:
  - vecdb://aml/aml_nesting
  - regulatory://correspondent/nesting_policy
---

# Nested Correspondent

> Status: 🟢 validated | Confidence: 79%

## Definition

**Nested Correspondent** activity routes payments through respondent banks lacking
direct relationship with the originator bank, obscuring ultimate originator identity.
Policy requires knowing downstream correspondents; nesting breaches transparency.

## Monitoring Signals

- MT103 field inconsistencies — ordering institution not in KYC relationship path
- Volume spike through dormant correspondent sub-account
- High-risk jurisdiction nesting under low-risk parent BIC
- Unable to identify originator within SLA after enhanced trace request

## Related Concepts

- [[Layering Chain]] — bank-rail layering analogue
- [[Shell Company Network]] — corporate nesting parallel

```adl:relation
source: "Nested Correspondent"
relation: related-to
target: "adl://private/ceiec-aml/aml-layering"
mapping_type: domain
confidence: 0.73
```

```adl:relation
source: "Nested Correspondent"
relation: indexed-phrase
target: "x7k9n41tgap"
mapping_type: lexical
confidence: 0.90
```

```adl:evidence
evidence_type: cross_reference
data_ref: regulatory://correspondent/nesting_policy
description: "Internal correspondent banking nesting policy breach codes"
confidence: 0.90
observed_at: "2025-01-01T00:00:00Z"
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_nesting
description: "SWIFT path entropy — unknown downstream BIC frequency"
confidence: 0.78
observed_at: "2026-02-20T13:00:00Z"
```
