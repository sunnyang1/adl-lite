---
adl_type: concept
adl_id: aml-nominee-acct
status: validated
confidence: 0.80
novelty: 0.35
domain: financial_aml
mechanism: compositional_blend
scope: private/ceiec-aml
provisional_names:
  zh: "名义账户"
  en: "Nominee Account"
evidence_refs:
  - vecdb://aml/aml_nominee_acct
  - regulatory://fatf/beneficial_ownership
---

# Nominee Account

> Status: validated | Confidence: 80%

## Definition

A **Nominee Account** is held in the name of a stand-in party while a hidden controller
directs flows and beneficial interest. Nominee arrangements obscure UBO linkage in
corporate and retail channels. Monitoring pairs KYC nominee declarations with transaction
behavior inconsistent with stated occupation or income.

## Related Concepts

- [[Beneficial Owner Gap]] — opacity between nominee and UBO
- [[Shell Company Network]] — corporate nominee stacks
- [[Money Mule Account]] — sometimes conflated; mules may be witting or unwitting

```adl:relation
source: "Nominee Account"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-ben-owner"
mapping_type: ontological
confidence: 0.83
```

```adl:relation
source: "Nominee Account"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-shell-co"
mapping_type: statistical
confidence: 0.77
```

```adl:evidence
evidence_type: cross_reference
data_ref: regulatory://fatf/beneficial_ownership
description: "FATF beneficial ownership transparency linkage"
confidence: 0.85
observed_at: "2025-01-01T00:00:00Z"
```
