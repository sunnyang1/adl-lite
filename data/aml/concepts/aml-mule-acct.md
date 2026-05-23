---
adl_type: concept
adl_id: aml-mule-acct
status: validated
confidence: 0.84
novelty: 0.36
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "钱骡账户"
  en: "Money Mule Account"
evidence_refs:
  - vecdb://aml/aml_mule_acct
  - fraud://mule/network_intel
---

# Money Mule Account

> Status: 🟢 validated | Confidence: 84%

## Definition

A **Money Mule Account** receives third-party illicit funds and forwards them quickly,
often for fee or coercion. Mules show pass-through behavior, young account age, and
disconnect between customer profile and counter-party risk geography.

## Monitoring Signals

- Account age <90 days with inbound >5× historical outbound median
- ≥80% outbound to crypto exchanges or high-risk corridors within 24h of inbound
- Customer login geo inconsistent with counter-party countries
- Multiple unrelated inbound senders within 48h

## Related Concepts

- [[Smurfing Pattern]] — mules collect structured deposits
- [[Peripheral Attention Trap]] — mule accounts often peripheral nodes
- [[Rapid Movement]] — outbound velocity signature

```adl:relation
source: "Money Mule Account"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-smurfing"
mapping_type: statistical
confidence: 0.80
```

```adl:relation
source: "Money Mule Account"
relation: related-to
target: "adl://private/ceiec-aml/aml-attention-trap"
mapping_type: domain
confidence: 0.68
```

```adl:evidence
evidence_type: cross_reference
data_ref: fraud://mule/network_intel
description: "Fraud intelligence mule network overlap on account graph"
confidence: 0.86
observed_at: "2026-03-01T00:00:00Z"
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_mule_acct
description: "Pass-through ratio and inbound sender entropy feature cluster"
confidence: 0.83
observed_at: "2026-03-18T11:00:00Z"
```
