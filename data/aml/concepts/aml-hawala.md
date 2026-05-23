---
adl_type: concept
adl_id: aml-hawala
status: validated
confidence: 0.82
novelty: 0.42
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "非正式价值转移"
  en: "Informal Value Transfer"
evidence_refs:
  - vecdb://aml/aml_hawala
---

# Informal Value Transfer

> Status: 🟢 validated | Confidence: 82%

## Definition

**Informal Value Transfer** (hawala-style) moves value via trust and offsetting books
without parallel SWIFT messages. Legitimate remittance corridors exist; AML focus is on
volume mismatch, mirror payouts, and absence of trade or family remittance rationale.

## Monitoring Signals

- Mirror inbound/outbound amounts across unrelated customers within hours
- High-risk corridor concentration without documentary remittance purpose
- Agent settlement pattern: many small credits, one large debit to hawaladar account
- Customer profile inconsistent with cross-border flow frequency

## Related Concepts

- [[Rapid Movement]] — speed similarity without formal rails
- [[Layering Chain]] — informal legs alternate with formal wires

```adl:relation
source: "Informal Value Transfer"
relation: analogical-transfer
target: "adl://public/concepts/informal_value_transfer_systems"
mapping_type: ontological
confidence: 0.75
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_hawala
description: "Mirror settlement graph without trade finance anchors"
confidence: 0.80
observed_at: "2025-12-12T07:00:00Z"
```

```adl:evidence
evidence_type: human_expert
data_ref: expert://aml_team/remittance_desk_2025
description: "Remittance desk hawala indicator calibration session"
confidence: 0.87
observed_at: "2026-01-08T15:00:00Z"
```
