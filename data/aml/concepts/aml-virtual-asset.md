---
adl_type: concept
adl_id: aml-virtual-asset
status: validated
confidence: 0.83
novelty: 0.41
domain: financial_aml
scope: private/ceiec-aml
provisional_names:
  zh: "虚拟资产网关"
  en: "Virtual Asset Gateway"
evidence_refs:
  - vecdb://aml/aml_virtual_asset
  - chain://vasp/travel_rule_feed
---

# Virtual Asset Gateway

> Status: 🟢 validated | Confidence: 83%

## Definition

A **Virtual Asset Gateway** is the on-ramp/off-ramp interface where fiat and virtual assets
convert at VASP or MSB nodes. Laundering exploits rapid cycling: fiat → crypto → fiat with
minimal holding time and jurisdictional arbitrage across VASP policies.

## Monitoring Signals

- Fiat deposit to exchange followed by full withdrawal within 6 hours
- Travel Rule counter-party data missing on high-value transfers
- VASP hop count >4 before fiat off-ramp to different country
- Customer risk tier inconsistent with privacy-coin usage share

## Related Concepts

- [[Crypto Mixer Exposure]] — privacy layer after gateway entry
- [[Rapid Movement]] — fiat-crypto-fiat velocity

```adl:relation
source: "Virtual Asset Gateway"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-crypto-mix"
mapping_type: statistical
confidence: 0.84
```

```adl:evidence
evidence_type: cross_reference
data_ref: chain://vasp/travel_rule_feed
description: "Travel Rule completeness score below VASP policy floor"
confidence: 0.86
observed_at: "2026-04-01T00:00:00Z"
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_virtual_asset
description: "Fiat-crypto-fiat cycle time and jurisdiction spread features"
confidence: 0.82
observed_at: "2026-04-20T09:00:00Z"
```
