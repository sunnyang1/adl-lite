---
adl_type: concept
adl_id: aml-smurfing
status: validated
confidence: 0.82
novelty: 0.25
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "拆分存款模式"
  en: "Smurfing Pattern"
evidence_refs:
  - vecdb://aml/aml_smurfing
  - regulatory://fatf/rec16_structuring
---

# Smurfing Pattern

> Status: 🟢 validated | Confidence: 82%

## Definition

**Smurfing** (structuring) splits large illicit proceeds into many sub-threshold deposits
or withdrawals across accounts controlled by the same beneficial owner network. Each
leg appears innocuous; aggregate flow reconstructs placement volume above reporting limits.

## Monitoring Signals

- Many same-day cash deposits between 80–99% of local CTR threshold
- Shared device fingerprint or IP across geographically dispersed depositors
- Round-dollar amounts with low merchant diversity
- Rapid consolidation transfer within 24h to a single internal account

## Related Concepts

- [[CTR Threshold Avoidance]] — direct specialisation of threshold gaming
- [[Money Mule Account]] — smurfs often deposit through mule wallets
- [[Cash Integration]] — placement stage following smurfed cash-in

```adl:relation
source: "Smurfing Pattern"
relation: specialisation-of
target: "adl://public/concepts/money_laundering_placement"
mapping_type: ontological
confidence: 0.85
```

```adl:relation
source: "Smurfing Pattern"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-ctr-avoid"
mapping_type: statistical
confidence: 0.88
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_smurfing
description: "Deposit amount histogram spike just below CTR with shared beneficiary graph"
confidence: 0.84
observed_at: "2025-11-02T08:00:00Z"
```

```adl:evidence
evidence_type: cross_reference
data_ref: regulatory://fatf/rec16_structuring
description: "FATF Recommendation 16 structuring typology alignment"
confidence: 0.90
observed_at: "2025-01-01T00:00:00Z"
```
