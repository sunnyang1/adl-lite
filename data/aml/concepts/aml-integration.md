---
adl_type: concept
adl_id: aml-integration
status: validated
confidence: 0.87
novelty: 0.15
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "融合阶段"
  en: "Integration Stage"
evidence_refs:
  - regulatory://fatf/integration
  - vecdb://aml/aml_integration
---

# Integration Stage

> Status: validated | Confidence: 87%

## Definition

The **Integration Stage** reintroduces laundered value into the legitimate economy with
apparent lawful origin. Integration paths include real-estate purchase, casino chip
conversion, invoice-backed trade settlement, and salary-like disbursements through shell
payroll. Graph analytics focus on sink accounts with sustained outflows to merchants
and asset brokers.

## Related Concepts

- [[Real Estate ML]] — property integration channel
- [[Casino Chip Laundering]] — gaming instrument integration
- [[Shell Company Network]] — corporate veil at integration

```adl:relation
source: "Integration Stage"
relation: specialisation-of
target: "adl://public/concepts/money_laundering_integration"
mapping_type: ontological
confidence: 0.94
```

```adl:relation
source: "Integration Stage"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-real-estate"
mapping_type: statistical
confidence: 0.79
```

```adl:evidence
evidence_type: cross_reference
data_ref: regulatory://fatf/integration
description: "FATF integration typology anchor"
confidence: 0.91
observed_at: "2025-01-01T00:00:00Z"
```
