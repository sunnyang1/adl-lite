---
adl_type: concept
adl_id: aml-cuckoo-smurf
status: provisional
confidence: 0.76
novelty: 0.55
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  zh: "布谷鸟拆分"
  en: "Cuckoo Smurfing"
evidence_refs:
  - regulatory://fatf/cuckoo_smurfing
  - vecdb://aml/aml_cuckoo_smurf
---

# Cuckoo Smurfing

> Status: provisional | Confidence: 76%

## Definition

**Cuckoo Smurfing** places illicit cash into third-party bank accounts without account
holder knowledge, mimicking legitimate inbound remittances. Victim accounts receive
structured deposits while controllers withdraw matching sums elsewhere. The typology
combines smurfing mechanics with identity misuse distinct from voluntary money mules.

## Related Concepts

- [[Smurfing Pattern]] — shared sub-threshold fragmentation
- [[Money Mule Account]] — contrast voluntary mule vs victim account
- [[Informal Value Transfer]] — remittance mimicry corridor

```adl:relation
source: "Cuckoo Smurfing"
relation: specialisation-of
target: "adl://private/ceiec-aml/aml-smurfing"
mapping_type: ontological
confidence: 0.81
```

```adl:relation
source: "Cuckoo Smurfing"
relation: co-occurs-with
target: "adl://private/ceiec-aml/aml-mule-acct"
mapping_type: statistical
confidence: 0.65
```

```adl:evidence
evidence_type: cross_reference
data_ref: regulatory://fatf/cuckoo_smurfing
description: "FATF cuckoo smurfing alert typology"
confidence: 0.78
observed_at: "2025-06-01T00:00:00Z"
```
