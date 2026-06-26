# ADL Lite Ontology Specification

> **⚠️ 已废弃 (Obsolete):** 本文档是静态 OWL/SHACL 概念规范，已被操作本体 `adl_lite/adl_core_ontology.yaml` (由 `OntologyManager` 加载) 取代。当前项目使用 YAML 注册表定义类、谓词、动作和转换规则。如需查看最新的操作本体定义，请直接查阅 `adl_lite/adl_core_ontology.yaml`。如需了解语义网导出，请参考 `adl_lite/owl_export.py` 和 `adl_lite/rdfstar_export.py`。

This document provides the machine-readable ontology specification for ADL Lite, comprising OWL 2 DL class definitions and SHACL shape constraints.

---

## Files

| File | Purpose | Format |
|------|---------|--------|
| `adl_lite_ontology.ttl` | OWL 2 DL class and property definitions | Turtle |
| `adl_lite_shacl.ttl` | SHACL validation shapes | Turtle |

---

## OWL 2 DL Ontology (`adl_lite_ontology.ttl`)

### Prefixes

| Prefix | URI |
|--------|-----|
| `adl` | `http://adl-lite.org/ontology#` |
| `bfo` | `http://purl.obolibrary.org/obo/BFO_` |
| `iao` | `http://purl.obolibrary.org/obo/IAO_` |
| `ufo` | `http://ufo-ontology.org/ontology#` |
| `prov` | `http://www.w3.org/ns/prov#` |
| `xsd` | `http://www.w3.org/2001/XMLSchema#` |
| `rdfs` | `http://www.w3.org/2000/01/rdf-schema#` |
| `owl` | `http://www.w3.org/2002/07/owl#` |
| `rdf` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` |

### Classes

| Class | Superclasses | Description |
|-------|-------------|-------------|
| `adl:Event` | `bfo:occurrent` (`BFO_0000003`), `prov:Entity` | A discrete occurrent in an event chain |
| `adl:EventChain` | `bfo:process` (`BFO_0000015`), `iao:information_content_entity` (`IAO_0000030`), `prov:Collection` | An ordered sequence of events constituting a process and an ICE |
| `adl:Concept` | `bfo:generically_dependent_continuant` (`BFO_0000040`), `prov:Entity` | The subject of an event chain |
| `adl:Relation` | `ufo:Relator`, `prov:Entity` | A relator mediating between concepts |

### Object Properties

| Property | Domain | Range | Inverse | Notes |
|----------|--------|-------|---------|-------|
| `adl:hasPreviousEvent` | `adl:Event` | `adl:Event` | `adl:hasNextEvent` | Immediate predecessor (NOT transitive) |
| `adl:hasNextEvent` | `adl:Event` | `adl:Event` | `adl:hasPreviousEvent` | Immediate successor |
| `adl:hasForkTarget` | `adl:Event` | `adl:Concept` | — | Links a fork event to its target |
| `adl:wasValidatedBy` | `adl:Event` | `prov:Agent` | — | Sub-property of `prov:wasAssociatedWith` |
| `adl:wasDeprecatedBy` | `adl:Event` | `prov:Agent` | — | Sub-property of `prov:wasAssociatedWith` |
| `adl:hasEvent` | `adl:EventChain` | `adl:Event` | — | Links a chain to its member events |

### Data Properties

| Property | Domain | Range | Description |
|----------|--------|-------|-------------|
| `adl:hasHash` | `adl:Event` | `xsd:string` | SHA-256 hash of the canonicalised event |
| `adl:hasEventID` | `adl:Event` | `xsd:string` | Unique event identifier |
| `adl:hasTimestamp` | `adl:Event` | `xsd:dateTime` | ISO-8601 timestamp |
| `adl:hasConfidence` | `adl:Event` | `xsd:float` | Confidence score [0,1] |
| `adl:hasPayload` | `adl:Event` | `xsd:string` | JSON-encoded payload |
| `adl:eventType` | `adl:Event` | `xsd:string` | Event type from enumeration |
| `adl:hasConceptID` | `adl:EventChain`, `adl:Concept` | `xsd:string` | Concept identifier |
| `adl:hasStatus` | `adl:Concept` | `xsd:string` | Derived status |
| `adl:hasGenesisHash` | `adl:EventChain` | `xsd:string` | Genesis event hash (64-hex) |

### Individuals (Action Types)

| Individual | Type | Description |
|------------|------|-------------|
| `adl:registerAction` | `adl:Event` | Register a new concept |
| `adl:validateAction` | `adl:Event` | Validate a concept |
| `adl:deprecateAction` | `adl:Event` | Deprecate a concept |
| `adl:forkAction` | `adl:Event` | Fork a concept |
| `adl:archiveAction` | `adl:Event` | Archive a concept |

---

## SHACL Shapes (`adl_lite_shacl.ttl`)

### `adl:EventShape`

Constraints on `adl:Event` instances:

| Property | Constraint | Value |
|----------|-----------|-------|
| `adl:eventType` | `sh:datatype` | `xsd:string` |
| | `sh:minCount` / `sh:maxCount` | 1 / 1 |
| | `sh:in` | `REGISTER`, `VALIDATE`, `DEPRECATE`, `FORK`, `ARCHIVE`, `EVIDENCE`, `SNAPSHOT`, `RELATE`, `SEAL` |
| `adl:hasHash` | `sh:datatype` | `xsd:string` |
| | `sh:minCount` / `sh:maxCount` | 1 / 1 |
| | `sh:pattern` | `^[a-f0-9]{64}$` |
| `prov:wasAssociatedWith` | `sh:class` | `prov:Agent` |
| | `sh:minCount` / `sh:maxCount` | 1 / 1 |
| `prov:startedAtTime` | `sh:datatype` | `xsd:dateTime` |
| | `sh:minCount` / `sh:maxCount` | 1 / 1 |

### `adl:EventChainShape`

Constraints on `adl:EventChain` instances:

| Property | Constraint | Value |
|----------|-----------|-------|
| `adl:hasEvent` | `sh:class` | `adl:Event` |
| | `sh:minCount` | 1 |
| `adl:hasConceptID` | `sh:datatype` | `xsd:string` |
| | `sh:minCount` / `sh:maxCount` | 1 / 1 |
| `adl:hasGenesisHash` | `sh:datatype` | `xsd:string` |
| | `sh:minCount` / `sh:maxCount` | 1 / 1 |
| | `sh:pattern` | `^[a-f0-9]{64}$` |

### `adl:ConceptShape`

Constraints on `adl:Concept` instances:

| Property | Constraint | Value |
|----------|-----------|-------|
| `adl:hasConceptID` | `sh:datatype` | `xsd:string` |
| | `sh:minCount` / `sh:maxCount` | 1 / 1 |
| `adl:hasStatus` | `sh:datatype` | `xsd:string` |
| | `sh:minCount` / `sh:maxCount` | 1 / 1 |
| | `sh:in` | `provisional`, `validated`, `deprecated`, `forked`, `archived` |
| `adl:hasConfidence` | `sh:datatype` | `xsd:float` |
| | `sh:minCount` / `sh:maxCount` | 0 / 1 |
| | `sh:minInclusive` / `sh:maxInclusive` | 0.0 / 1.0 |

---

## Alignment with Foundational Ontologies

| ADL Lite | BFO | DOLCE | UFO | IAO | PROV-O |
|-----------|-----|-------|-----|-----|--------|
| Event | occurrent | perdurant | event | — | Activity |
| EventChain | process | — | — | information content entity | Collection |
| Concept | generically dependent continuant | — | — | information content entity | Entity |
| Relation | — | — | relator | — | Association |

---

## Known Limitations

1. **OWL 2 DL Expressivity**: The ontology is in the OWL 2 DL fragment (no metamodeling, no transitive closure over `hasPreviousEvent` as a transitive property). The immediate-predecessor link `adl:hasPreviousEvent` is intentionally **not** declared `Transitive` because transitivity would make every ancestor a "previous event," destroying the chain semantics.
2. **SHACL vs OWL Property Names**: The SHACL shapes use the same property URIs as the OWL ontology (e.g., `adl:hasHash` rather than `adl:eventHash`) to ensure alignment.
3. **Action Type Encoding**: Action types are encoded as individuals in OWL and as string enumerations in SHACL. Full alignment between the individual-based taxonomy and the string-based validation requires a future bridge (e.g., `owl:oneOf` enumeration in OWL).
