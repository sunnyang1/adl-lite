---
adl_type: concept
adl_id: aml-crypto-mix
status: validated
confidence: 0.84
novelty: 0.45
domain: financial_aml
mechanism: compositional_blend
scope: private/ceiec-aml
provisional_names:
  zh: "混币器暴露"
  en: "Crypto Mixer Exposure"
evidence_refs:
  - vecdb://aml/aml_crypto_mix
  - chain://labels/tumbler_v2
---

# Crypto Mixer Exposure

> Status: 🟢 validated | Confidence: 84%

## Definition

**Crypto Mixer Exposure** flags wallet activity with direct or one-hop interaction to
known tumbler smart contracts or custodial mixers. Exposure does not prove illicit intent
but raises prior probability when combined with off-ramp fiat spikes or trade-finance gaps.

## Monitoring Signals

- Inbound funds from labeled mixer contracts within 3 hops
- Peel-chain pattern: sequential outbound amounts just below exchange minimums
- Rapid swap through privacy coins then stablecoin off-ramp
- Address co-spend with darknet marketplace clusters

## Related Concepts

- [[Virtual Asset Gateway]] — fiat on/off ramp pairing
- [[Layering Chain]] — crypto legs in cross-asset paths

```adl:relation
source: "Crypto Mixer Exposure"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-virtual-asset"
mapping_type: statistical
confidence: 0.86
```

```adl:relation
source: "Crypto Mixer Exposure"
relation: related-to
target: "adl://private/ceiec-aml/aml-layering"
mapping_type: domain
confidence: 0.71
```

```adl:evidence
evidence_type: cross_reference
data_ref: chain://labels/tumbler_v2
description: "On-chain label feed v2 — mixer interaction within 2-hop window"
confidence: 0.88
observed_at: "2026-04-01T00:00:00Z"
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://aml/aml_crypto_mix
description: "Wallet embedding distance to known tumbler seed set <0.15"
confidence: 0.82
observed_at: "2026-04-15T14:00:00Z"
```
