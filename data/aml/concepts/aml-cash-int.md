---
adl_type: concept
adl_id: aml-cash-int
status: validated
confidence: 0.80
novelty: 0.26
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "现金整合"
  en: "Cash Integration"
evidence_refs:
  - vecdb://aml/aml_cash_int
---

# Cash Integration

> Status: 🟢 validated | Confidence: 80%

## Definition

**Cash Integration** is the laundering stage where illicit cash enters the legitimate
economy through businesses with high cash turnover (retail, hospitality, MSBs). Monitoring
focuses on deposit patterns inconsistent with seasonality and inventory turnover.

## Monitoring Signals

- Cash deposit share >80% for e-commerce declared business model
- Night-shift ATM deposits exceeding staffed hours capacity
- Sequential branch deposits across city within 2 hours
- Invoice-free supplier payments from cash-heavy revenue account

## Related Concepts

- [[Smurfing Pattern]] — placement before integration
- [[Casino Chip Laundering]] — gaming-sector integration variant

```adl:relation
source: "Cash Integration"
relation: specialisation-of
target: "adl://public/concepts/money_laundering_integration"
mapping_type: ontological
confidence: 0.88
```

```adl:relation
source: "Cash Integration"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-smurfing"
mapping_type: statistical
confidence: 0.79
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_cash_int
description: "Sector cash-intensity prior vs observed deposit mix divergence"
confidence: 0.80
observed_at: "2025-07-14T16:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: expert://aml_team/cash_int_review_2025
description: "Sector playbook review — hospitality MSB integration typologies"
confidence: 0.86
observed_at: "2025-11-01T10:00:00Z"
```
