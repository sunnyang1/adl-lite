# Ontology as a Middle Layer for ADL Lite

**Status:** Proposal (Phase 2+ direction)  
**Audience:** ADL Lite maintainers, AAMAS paper authors  
**Related:** `docs/SPEC.md`, `adl_lite/models.py`, `adl_lite/validator.py`, `adl_lite/memory.py`, `adl_lite/consensus.py`

---

## 中文摘要

**Ontology 在 ADL Lite 中的含义**：不是哲学本体论，而是位于 SQLite/NetworkX 存储之上、面向 Agent 的**语义契约层**——统一定义概念类型、关系谓词、域标签、状态机规则与 scope ACL，使 L1/L2/L3 文档可被一致地校验、查询与跨域对齐（如 `isomorphic-to`）。

**相对纯关系数据库的优势**：DB 存事实与索引；Ontology 层存**可执行的语义规则**（合法谓词、状态转移、跨域映射类型、scope 可见性），让 Agent 在写入/检索前获得结构化约束，而非事后 SQL 拼装。

**与现有 ADL 的契合度**：高。L3 块已是 RDF 三元组形态；`ADLValidator`、`ConsensusEngine`、`WarmIndex.relations` 已实现约 60–70% 的"轻量 ontology"职责。缺口是**集中式 schema registry**、**谓词闭包**、**可选 OWL 导出**。

**推荐方案**：Path A — 纯 Python `OntologyManager`（无 OWL 运行时），Phase 2 落地；Path B — 可选 Turtle/OWL 导出，Phase 3 评估。

**下一步**：定义 ADL Core Ontology YAML → 接入 validator → 暴露 agent tools → 写 ablation issue。

---

## Design philosophy

**Positioning one-liner:**

> **Markdown-native operational ontology for multi-agent concept consensus**

ADL Lite 的架构选择是 CS/KR 意义上的 **ontology**（轻量语义中间层），**不是**用 phenomenology 替代技术栈。二者在此项目中 **同名异义**：phenomenology（过程性、叙事性、情境意义）提供 **设计约束**；ontology（类型、谓词、状态机、scope 语法）提供 Agent 可查询的 **可执行契约**。

**Operational ontology framing:** 借鉴 Palantir 式 semantic + kinetic 分层——有治理的类型与关系、生命周期感知的协调——但避免企业级知识图谱、内嵌 OWL 推理器或 triple store 成为部署前提。Markdown 仍是 authoring surface；ontology 层约束并解释 SQLite/NetworkX 中的持久化数据。

| 路线 | ADL Lite 立场 |
|------|---------------|
| **纯 DB**（谓词为 opaque TEXT、ACL 逻辑散落查询） | Warm 层存事实与索引；ontology 发布谓词注册表、转移图、scope 语法 |
| **重型 OWL/推理器**（HermiT、Protégé 运行时、SPARQL-first） | Path A：`OntologyManager` + YAML；Path B：可选仅导出 Turtle — 无内嵌推理 |
| **以 phenomenology 代栈**（叙事取代 schema） | Phenomenology 约束设计；ontology + L2/L3 实现机制 |

| Phenomenological reminder | ADL Lite mechanism |
|---------------------------|-------------------|
| 意义在叙事中，而非实体快照 alone | **L2** Markdown + provisional names；L1 身份不冻结正文 |
| 知识是过程性的，非静态目录 | **ConsensusEngine** 状态机 + append-only 共识链 |
| 跨域对齐须显式断言，不可自动推断 | L3 **`isomorphic-to`** + **`mapping_type`**；人/Agent 断言 |
| 情境决定可见性 | **Scope ACL** + namespace grammar |
| 避免 ontology-as-rigid-database | **SQLite + NetworkX** 持久化；ontology **位于其上**，非替代 |

Product copy: [`docs/PRD.md`](../PRD.md) §2 Design philosophy.

---

## 1. What "Ontology" Means Here

In ADL Lite, **ontology** is a **project-local semantic schema** that sits between persistent storage and agent-facing APIs. It is *not* a philosophical treatise on being, nor a mandate to deploy HermiT, Protégé, or a triple store on day one.

Concretely, the ontology layer answers four questions that a relational database alone leaves implicit:

| Question | Ontology layer provides | Already in v0.1? |
|----------|-------------------------|------------------|
| What *kinds* of things exist? | Closed or extensible class set (`discovery`, `concept`, …) | Partial — `ADLType` enum in Pydantic |
| What *relations* are legal? | Predicate registry (`isomorphic-to`, `specialisation-of`, …) | No — free string in L3 |
| What *rules* govern change? | Status transition graph, fork policies | Yes — `ConsensusEngine._is_valid_transition` |
| Who *sees* what? | Scope namespace + ACL semantics | Yes — `ADLValidator.validate_scope_access` |

The ontology layer **does not replace** `ADLMemory` (SQLite + NetworkX). It **constrains and interprets** what gets stored there. Documents remain Markdown-native; the ontology is the machine-readable contract agents consult before read/write.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Agents / CLI / MCP tools  (adl_parse, adl_store, adl_validate) │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│              Ontology Semantic Layer  (NEW — proposed)            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Class/Type   │ │ Predicate    │ │ Policy rules             │ │
│  │ registry     │ │ registry     │ │ invariants   │ │
│  │ (ADLType,    │ │ (isomorphic- │ │ (status machine, scope   │ │
│  │  domain tags)│ │  to, …)      │ │  ACL, mapping_type)      │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
│         ▲ optional OWL/Turtle export (Path B, Phase 3)          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│  ADLValidator + ConsensusEngine  (EXISTING — schema consumers)    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│  ADLMemory — Hot / Warm / Cold                                    │
│  ┌────────────┐  ┌─────────────────────────────────────────────┐│
│  │ HotIndex   │  │ WarmIndex: SQLite documents + relations     ││
│  │ (skeleton) │  │            + NetworkX DiGraph (optional)    ││
│  └────────────┘  └─────────────────────────────────────────────┘│
│  Cold: file archive (deferred in v0.1)                            │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow:** Agent authors L1/L2/L3 Markdown → parser → **ontology validates against registry** → validator (SSA, scope) → memory stores document + relation edges → graph/SQL queries return scope-filtered, status-aware results.

---

## 3. Advantages vs Relational DB–Only

For ADL's specific workloads, a semantic middle layer adds value *on top of* SQLite, not instead of it.

### 3.1 Typed relations (L3)

| DB-only approach | With ontology layer |
|------------------|---------------------|
| `relations(predicate: `(source, predicate,
 predicate, target, confidence)` — predicate is opaque TEXT | Predicate registry defines domain/range, symmetry, transitivity hints |
| Invalid `relation: "similar"` passes insert | Validator rejects unknown predicates (configurable strict mode) |
| Cross-domain `isomorphic-to` is just another row | `mapping_type` (`topological`, `ontological`, `structural`) tied to mechanism enum |

**Pilot evidence:** RQ3 L3-only retrieval ablation shows relation-typed signal matters for relation-sensitive queries (`packages (`docs/paper/DRAFT.md` §2.3). An ontology layer makes that signal *governed*, not accidental.

### 3.2 Scope ACL

SQLite stores `scope` as a column. Ontology layer encodes the **namespace grammar** (`public`, `private/<org>`, …) and **access lattice** once, shared by validator, memory prefilter, and agent tools. DB-only replication scatters regex/prefix logic across queries.

**Pilot evidence:** RQ4 — 99/99 cross-scope probes denied (33 indexed concepts × 3 requesters; `ADLValidator.validate_scope_access`).

### 3.3 Status machine

A CHECK constraint on `status` ENUM catches typos; it does not encode **legal transitions** or fork lineage. `ConsensusEngine` already implements a transition graph — ontology layer would **publish** that graph as schema metadata agents can introspect ("can I deprecate from `forked`?").

### 3.4 Cross-domain `isomorphic-to`

AML `capital_reflux_trap` → public `gradient_explosion` with `mapping_type: topological` is ADL's core cross-domain pattern. DB-only: two string IDs and a predicate. Ontology layer: declares `isomorphic-to` as a first-class object property with expected `mapping_type` values, optional domain compatibility rules, and merge thresholds aligned with `ForkManager.ISOMORPHISM_THRESHOLD` (0.90).

---

## 4. OWL/RDF ↔ ADL Lite Mapping

| OWL/RDF concept | ADL Lite equivalent | Module / layer |
|-----------------|---------------------|----------------|
| `owl:Class` | `ADLType` enum (`discovery`, `concept`, …) | L1 `adl_type`, `models.py` |
| `owl:NamedIndividual` | Document instance identified by `adl_id` | L1 front matter |
| `owl:ObjectProperty` | L3 `relation` predicate | `ADLRelationBlock.relation` |
| `owl:DatatypeProperty` | L1 scalars (`confidence`, `novelty`, `domain`) | `ADLFrontMatter` |
| `rdfs:label` | `provisional_names.zh` / `.en` | L1 |
| `rdfs:comment` | L2 Markdown body | `ADLDocument.markdown_body` |
| `owl:AnnotationProperty` | Evidence metadata, seal status | L3 `adl:evidence`, `adl:seal` |
| Reification / provenance | Consensus chain entries | `consensus.py` `ConsensusEntry` |
| `owl:versionInfo` / lineage | Fork registration + `forked` status | `ForkManager`, `ConsensusEngine.fork` |
| Namespace / import | Scope URI + `adl://` targets | L1 `scope`, L3 `target` |
| `owl:sameAs` / alignment | `isomorphic-to` + `mapping_type` | L3 relation blocks |
| SHACL shape | SSA + slot validation rules | `ADLValidator` |
| SPARQL | Not implemented | Future; today: SQL + NetworkX BFS |
| Reasoner (HermiT, etc.) | **Not implemented** | Out of scope Phase 1–2 |

**Key insight:** ADL Lite v0.1 is already a **pragmatic, author-editable subset** of RDF-style modeling. The missing piece is a **central schema artifact** agents and validators share, not a format change.

---

## 5. Implementation Paths

### Path A — Lightweight `OntologyManager` (recommended, no OWL runtime)

A Python module (`adl_lite/ontology.py`, proposed) loading a YAML/JSON **ADL Core Ontology** file:

```yaml
# adl_core_ontology.yaml (sketch)
classes:
  discovery:
    required_l1: [mechanism]
predicates:
  isomorphic-to:
    symmetric: false
    allowed_mapping_types: [topological, ontological, structural]
  specialisation-of:
    transitive: true
status_transitions:  # mirrors ConsensusEngine
  provisional: [validated, deprecated, forked, archived]
scopes:
  prefixes: [public, private, user, shared]
```

**Responsibilities:**
- Validate L3 predicates against registry (extend `ADLValidator`)
- Expose `list_predicates()`, `allowed_transitions(status)`, `resolve_uri(adl_id, scope)` for tools
- Optional: derive NetworkX edge labels from registry metadata

**Dependencies:** None beyond existing stack (Pydantic, PyYAML).

### Path B — Optional OWL/Turtle export (Phase 3+)

- One-way export: ADL documents + core ontology → Turtle for interoperability (Wikidata, Protégé review)
- **No** embedded reasoner in ADL Lite; external tools may consume export
- Evaluate whether `rdflib` serialization cost is justified by user demand

### Phased Roadmap

| Phase | Deliverable | Effort |
|-------|-------------|--------|
| **2a** | `adl_core_ontology.yaml` + predicate validation in `ADLValidator` | ~1 week |
| **2b** | `OntologyManager` API + CLI `adl-lite ontology validate` | ~1 week |
| **2c** | Agent tool `adl_ontology_query` for predicate/transition introspection | ~3 days |
| **3** | Turtle export stub + cross-store alignment experiment | TBD |
| **3+** | SPARQL endpoint or SHACL export — only if Phase 3 export proves useful | TBD |

---

## 6. What NOT to Claim

Avoid overstating current or near-term capabilities:

| Do NOT claim | Reality in v0.1 / proposal |
|--------------|----------------------------|
| HermiT / Pellet / OWL reasoning integrated | No reasoner; Path B is export-only |
| Production-scale knowledge graph (millions of triples) | Pilot corpus: 20 AML concepts, 25 retrieval queries |
| Ontology replaces SQLite or NetworkX | Ontology sits **above** warm storage |
| Automatic cross-domain inference | `isomorphic-to` is asserted, not inferred |
| Cold tier operational | Spec §9 — deferred |
| Vector ANN in warm layer | Spec §9 non-goal; TF-IDF pilot only |
| Distributed blockchain consensus | `ConsensusEngine` is append-only **local** audit log, not PoW/PoS |
| Full OWL 2 DL expressiveness | Closed predicate set + simple rules only (Path A) |
| RQ1 universal clarity win | Fair-plain controls show Δ=0; gain vs unstructured notes only |
| Enterprise ontology governance workflow | No Protégé plugin, no curator UI |

---

## 7. AAMAS Paper Positioning (paste-ready)

> ADL Lite occupies a deliberate middle ground between unstructured Markdown and heavyweight ontology pipelines: L3 relation blocks provide RDF-like triples editable in ordinary Markdown, while SSA validation, scope ACL, and an append-only consensus chain supply machine-checkable coordination primitives without requiring a triple store or OWL reasoner. Phase 1 pilots (n=20 AML concepts) show mechanistic gains in lifecycle traceability, scope isolation, and L3-sensitive retrieval rather than claims of automated ontological inference. We argue that a lightweight, document-native semantic layer—future-work centralized in an `OntologyManager` schema—can deliver multi-agent auditability at deployment cost closer to Git-backed notes than enterprise knowledge graphs.

---

## 8. Open Questions / GitHub Issue Checklist

- [ ] **Predicate closure:** Should `relation` values be an open string (extensible per domain) or a closed core set with `domain/` prefixes?
- [ ] **mapping_type taxonomy:** Standardize `topological | ontological | structural | engineering` or keep free-form?
- [ ] **Ontology versioning:** How do schema changes affect stored documents (`ontology_version` in L1?)?
- [ ] **Cross-scope relation visibility:** Public targets from private docs — ontology rule vs current ad hoc URI check?
- [ ] **Fork merge semantics:** Should ontology encode `ForkManager.ISOMORPHISM_THRESHOLD` or remain policy in code?
- [ ] **Wiki-link → relation promotion:** Spec §9 defers auto-extraction; does ontology define eligible link types?
- [ ] **Evidence type ontology:** Close `EvidenceType` enum or allow domain extensions (`aml_case_file`, …)?
- [ ] **Export priority:** Turtle vs JSON-LD vs SHACL — which interoperability path matters for collaborators?
- [ ] **Evaluation:** New RQ — does predicate registry reduce invalid L3 writes in 5-agent sim?
- [ ] **Module boundary:** `ontology.py` vs extending `validator.py` — single owner for schema rules?

**Suggested first issue title:** `feat(ontology): ADL Core Ontology YAML + predicate validation (Path A Phase 2a)`

---

## 9. Gap Summary: Implemented vs New

| Capability | v0.1 (implemented) | Ontology middle layer (new) |
|------------|-------------------|----------------------------|
| Document types | `ADLType` enum | Published in external schema file |
| Relation triples | L3 blocks → SQLite `relations` | Predicate registry + validation |
| Graph traversal | NetworkX BFS / SQL fallback | Same; optional edge typing from registry |
| Status machine | `ConsensusEngine` hardcoded | Introspectable schema + same enforcement |
| Scope ACL | Regex + `validate_scope_access` | Centralized namespace model |
| Cross-domain links | `isomorphic-to` in examples | Governed property + mapping_type rules |
| OWL/RDF interop | Implicit (RDF-like L3) | Explicit export (Path B, optional) |
| Agent introspection | Parse/validate/store tools | `adl_ontology_query` (proposed) |

---

*Proposal v0.1 — aligned with ADL Lite spec v0.1 and paper draft v0.3.3. No code changes in this document.*
