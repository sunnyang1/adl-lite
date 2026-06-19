# ADL Lite — Product Requirements Document

> **⚠️ 过时警告 (Outdated):** 本文档停留在 PRD v0.1 / Phase 1 阶段。当前项目状态请参考:
> - **权威指南:** `AGENTS.md` (v0.2.0, 代码-论文对齐, 716 测试)
> - **生存路径:** `SURVIVAL_PATH.md` (最新执行追踪)
> - **技术规范:** `docs/SPEC.md` (正在更新至 v0.2.0)
> - **论文:** `docs/paper_ao/` (Applied Ontology 提交, 39页, 9 定理)

**Status:** Living doc (Phase 1 shipped; Phase 2+ tracks below)  
**Companion docs:** [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) (execution tasks), [`SPEC.md`](SPEC.md) (normative syntax), [`RESEARCH_STATEMENT.md`](RESEARCH_STATEMENT.md) (academic framing)  
**Ontology design:** [`proposals/ONTOLOGY_MIDDLE_LAYER.md`](proposals/ONTOLOGY_MIDDLE_LAYER.md)

---

## 1. Product vision

ADL Lite is a **Markdown-native discovery language and toolkit** for multi-agent teams: humans edit L1/L2/L3 documents in Git/Obsidian; agents parse, validate, index, and coordinate concept lifecycle via CLI, Python API, and optional MCP.

**Success for adopters:** A contributor can validate examples, store concepts in hybrid memory, run scripted multi-agent sims, and reproduce pilot metrics without a graph database or OWL reasoner.

**Positioning one-liner:**

> **Markdown-native operational ontology for multi-agent concept consensus**

---

## 2. Design philosophy

ADL Lite adopts CS/knowledge-representation **ontology** as the right architecture — a lightweight semantic middle layer above warm storage — **not** phenomenology as a technical substitute. The two terms are **同名异义** in this project: phenomenology (process, narrative, situated meaning) supplies **design constraints**; ontology (types, predicates, transitions, scope grammar) supplies the **executable contract** agents consult before read/write.

**Operational ontology framing:** Inspired by Palantir-style semantic + kinetic layers — governed types and relations, lifecycle-aware coordination — without enterprise graph bloat, embedded OWL reasoners, or a triple store on the critical path. Markdown remains the authoring surface; the ontology layer constrains and interprets what persists in SQLite/NetworkX.

| Alternative | ADL Lite stance |
|-------------|-----------------|
| **DB-only** (opaque TEXT predicates, scattered ACL regex) | Warm index for facts; ontology publishes predicate registry, transitions, scope grammar |
| **Heavy OWL/reasoner** (HermiT, Protégé runtime, SPARQL-first) | Path A: YAML `OntologyManager`; Path B: optional export-only Turtle — no embedded inference |
| **Phenomenology-as-stack** (narrative replaces schema) | Phenomenology informs design; ontology + L2/L3 deliver the mechanism |

| Phenomenological reminder | ADL Lite mechanism |
|---------------------------|-------------------|
| Meaning lives in narrative, not entity snapshots alone | **L2** Markdown body + provisional names; L1 identity without freezing prose |
| Knowledge is processual, not a static catalog | **ConsensusEngine** status machine + append-only audit chain |
| Cross-domain alignment is asserted, not inferred | L3 **`isomorphic-to`** with explicit **`mapping_type`**; human/agent assertion required |
| Context governs visibility | **Scope ACL** + namespace grammar (`public`, `private/<org>`, …) |
| Avoid rigid ontology-as-database | **SQLite + NetworkX** persist documents and edges; ontology sits **above**, not instead |

Detail: [`proposals/ONTOLOGY_MIDDLE_LAYER.md`](proposals/ONTOLOGY_MIDDLE_LAYER.md) §Design philosophy.

---

## 3. Architecture tracks

| Track | Role | Primary modules |
|-------|------|-----------------|
| **Document language** | L1 YAML + L2 prose + L3 `adl:*` blocks | `parser.py`, `models.py` |
| **Validation & policy** | SSA, scope ACL, evidence/slot rules | `validator.py` |
| **Consensus & forks** | Status machine, append-only chain, fork merge | `consensus.py` |
| **Warm storage** | SQLite documents + `relations` + NetworkX BFS | `memory.py` |
| **Agent surface** | CLI + `adl_lite.tools` (+ optional MCP) | `cli.py`, `tools.py` |
| **Ontology middle layer** *(Phase 2+)* | Schema registry above DB — types, predicates, transitions, scope grammar | `ontology.py` (proposed), extends `validator.py` |
| **Evaluation** | AML mini-dataset, RQ pilots, 5-agent harness | `data/aml/`, `experiments/` |

**Stack (bottom → top):** Markdown files → `ADLMemory` (Hot/Warm) → `ADLValidator` + `ConsensusEngine` → **Ontology semantic layer** → Agents / CLI / MCP.

The ontology layer **does not replace** SQLite or NetworkX; it **constrains and interprets** what is stored and exposes introspectable rules to agents.

---

## 4. Ontology middle layer (product track)

### 4.1 Problem

v0.1 already implements ~60–70% of a lightweight ontology: L3 triples, `ADLType` enum, hardcoded status transitions, scope ACL. Gaps: **central schema artifact**, **predicate closure**, **agent introspection** of rules, optional **RDF interop export**.

### 4.2 Paths

| Path | Description | When |
|------|-------------|------|
| **A (recommended)** | `OntologyManager` + `adl_core_ontology.yaml`; no OWL runtime | Phase 2 |
| **B (optional)** | One-way Turtle/OWL export for external tools; no embedded reasoner | Phase 3+ |

### 4.3 Phased milestones

| ID | Deliverable | Depends on | Success criteria (verifiable) |
|----|-------------|------------|-------------------------------|
| **2a** | `adl_core_ontology.yaml` — classes, predicates, `mapping_type`, status graph, scope prefixes | Phase 1 validator | Unknown L3 `relation` values fail in strict mode; `adl-lite validate examples/*.md` still passes on corpus; new unit tests for predicate rejection |
| **2b** | `adl_lite/ontology.py` + `OntologyManager`; validator loads registry; CLI `adl-lite ontology validate` (or equivalent) | 2a | `list_predicates()`, `allowed_transitions(status)` match `ConsensusEngine` behavior; no duplicate transition logic drift (tests) |
| **2c** | Agent tool `adl_ontology_query` (predicates, transitions, scope grammar) | 2b | Harness or `tools.py` can answer "legal transition from `forked`?" without reading source |
| **3** | Turtle export stub (Path B); cross-store alignment experiment | 2b, demand signal | Export of `examples/` + core ontology produces valid Turtle; documented as export-only in README/PRD |

**Status (2026-05):** 2a complete; 2b partial — `OntologyManager`, YAML-backed `ConsensusEngine`, `adl-lite ontology validate`, strict `isomorphic-to` / `mapping_type`. 2c not started.

### 4.4 Explicit non-goals (ontology)

Do **not** plan or claim in product copy: HermiT/Pellet integration, production-scale triple store, automatic cross-domain inference, ontology replacing SQLite/NetworkX, cold tier operational, vector ANN in warm layer (see proposal §6).

---

## 5. Phase 1 — shipped scope (baseline)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Parse L1/L2/L3 | Done | `adl-lite parse`, `tests/test_parser.py` |
| SSA + scope validation | Done | `adl-lite validate`, `tests/test_scope_access.py` |
| Store + graph related | Done | `adl-lite store` / `related`, `memory.py` |
| Consensus register/transition/verify | Done | `adl-lite consensus`, `consensus.py` |
| Agent tools parity with CLI | Done | `adl_lite/tools.py` |
| AML dataset + scripted 5-agent sim | Done | `data/aml/`, `experiments/harness.py` |
| Pilot RQ1–RQ4 numbers | Done | `docs/experiments/RESULTS.md` |

Phase 1 exit criteria remain in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) §Success criteria.

---

## 6. Phase 2 — experiments & ontology (Q3 2026)

| Workstream | Outcome |
|------------|---------|
| **W5 (eval)** | Embedding retrieval ablation, human/LLM rubrics where planned (`PHASE_B_PLAN.md`) |
| **W7 (ontology)** | Milestones 2a → 2c; optional RQ: invalid L3 write rate in 5-agent sim |

**Ontology track done when:** (1) core ontology YAML is single source of truth for predicates and transitions used by validator; (2) strict validation is opt-in and documented; (3) at least one agent-facing introspection API ships; (4) proposal open questions (predicate open vs closed set) resolved in SPEC or YAML comments.

---

## 7. Phase 3 — paper & interop (Q3–Q4 2026)

- ESWC / ISWC paper pack frozen against `RESULTS.md` and `docs/paper/DRAFT.md`
- Path B Turtle export evaluated (strong fit for ISWC Resource / ESWC In-Use interop claims); SPARQL/SHACL only if export proves useful
- MCP / round-trip authoring — stretch, not blocking ontology 2a–2c

---

## 8. Research & venue positioning

**Primary targets:** [ESWC 2027](https://eswc-conferences.org/) and [ISWC 2027](https://iswc2027.semanticweb.org/) — Semantic Web, ontology learning, and agentic knowledge-graph authoring tracks (e.g. LLMs4OL, In-Use, Resource).

**Secondary / backup:** AAMAS 2027 — multi-agent coordination and consensus-chain angle if SW venue fit is weaker than expected.

**Claim discipline:** Pilot-limited evidence on AML mini-corpus (**20** concepts, **25** retrieval queries at `k=10`); no production AML or automated ontological inference. Lead with ontology strict validation + L3-only RQ3 + RQ4; report fair-plain Δ=0 (RQ1), scenario-only retrieval Δ=0 (RQ3). **Human RQ1 cancelled** (2026-05-24) — subjective RQ1 via LLM-as-judge / proxy only.

**Positioning line (paper/product):**

> ADL Lite is a **Markdown-native operational ontology** for agentic knowledge-graph authoring: L3 `adl:*` blocks expose RDF-like triples in ordinary Markdown; a YAML predicate registry and schema-guided validation (Method D) gate agent writes without an embedded OWL reasoner; optional Turtle export (Path B) supports SW interop. Multi-agent **consensus chains** and scope ACL are coordination artifacts on top of that semantic layer—not the primary research claim. Phase 1 pilots emphasize L3-sensitive retrieval, lifecycle traceability, and scope isolation at pilot scale. A centralized `OntologyManager` (Phase 2) makes the schema explicit for agents while keeping deployment cost closer to Git-backed notes than enterprise knowledge graphs.

**Research questions** (unchanged): RQ1 ambiguity, RQ2 consensus cost, RQ3 retrieval, RQ4 scope leakage — see [`RESEARCH_STATEMENT.md`](RESEARCH_STATEMENT.md).

---

## 9. Related documents

| Doc | Use |
|-----|-----|
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Week-by-week tasks, dependency graph, Phase 1 checklist |
| [`proposals/ONTOLOGY_MIDDLE_LAYER.md`](proposals/ONTOLOGY_MIDDLE_LAYER.md) | Ontology architecture, OWL mapping table, open questions |
| [`AGENT_WORKFLOW.md`](AGENT_WORKFLOW.md) | Authoring prompts and agent roles |
| [`SPEC.md`](SPEC.md) | Normative L1/L2/L3 and validation rules |

---

*PRD v0.1 — aligned with ontology proposal v0.1 and ADL Lite spec v0.1.*
