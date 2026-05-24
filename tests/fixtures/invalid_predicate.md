---
adl_type: concept
adl_id: bad-predicate-concept
status: provisional
confidence: 0.5
novelty: 0.5
domain: test
scope: public
provisional_names:
  en: "Bad Predicate Concept"
---

# Bad Predicate Concept

Fixture for strict ontology validation: uses an unknown L3 relation predicate.

```adl:relation
source: "Bad Predicate Concept"
relation: similar
target: "adl://public/concepts/gradient_explosion"
mapping_type: domain
confidence: 0.5
```

```adl:evidence
evidence_type: empirical_observation
data_ref: "file://test/fixture"
description: "Fixture evidence block"
confidence: 0.5
```
