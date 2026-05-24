# ADL Lite: Schema-Guided Operational Ontology Authoring in Markdown for Agentic Knowledge Graphs

*Subtitle: closed predicate registry, L3 triples in prose, and pilot evidence for retrieval, scope, and lifecycle traceability*

Version note: Draft pack for `v0.3.3` (Wave 6b), consolidating abstract, introduction, related work, method, evaluation, discussion, and conclusion into one manuscript artifact.

Supporting artifacts:
- Results summary: [`docs/experiments/RESULTS.md`](../experiments/RESULTS.md)
- Table 2 roll-up: [`docs/paper/table2_results.md`](table2_results.md)
- Reproduction guide: [`docs/experiments/REPRODUCE.md`](../experiments/REPRODUCE.md)

---

## Abstract

Agent-authored knowledge still lands as unstructured Markdown or chat logs, leaving referents, typed relations, and lifecycle status implicit—too weak for schema-guided KG tooling, yet too heavy for many teams to adopt OWL-first pipelines. **ADL Lite** is a Markdown-native **operational ontology** contract: L1 YAML metadata, L2 prose under Structured Semantic Anchoring (SSA), L3 typed `adl:*` triple blocks, a closed YAML predicate registry (schema-guided validation, Method D), hybrid indexing, and optional strict gates—plus append-only consensus and scope ACL as coordination artifacts on the same file. We report Phase B pilots on an AML mini-corpus (`n=20` concepts, `25` retrieval queries) with fair-plain and unstructured baselines.

Against **unstructured** plain-LLM notes (`n=15`, Cursor-proxy judges), ADL L2 prose scores higher on referent clarity (mean ADL−plain ≈ **+1.5** on a 1–5 rubric); against **fair-plain** pairings that preserve the same wording minus ADL structure, judge means are **identical** (Δ=0), isolating the benefit of authoring discipline rather than lexical content alone. ADL records **8** scripted consensus transitions versus **0** for plain Markdown; retrieval at `k=10` improves on the full query set (hit recall **1.00** vs **0.80**, Δ**+0.20**) with gains concentrated in five L3-only probes (Δ**+1.00**) rather than twenty scenario queries (hit Δ**0.00**); scope ACL denies **99/99** cross-scope probes (33 indexed concepts × 3 requesters). We treat these as **pilot-limited** evidence: small samples, proxy adjudication, and synthetic AML stubs—not production AML or human-grounded benchmarks.

---

## 1. Introduction

When multiple agents converge on overlapping conceptual discoveries, they typically exchange unstructured prose—in practice, conversational logs and Markdown snippets that bury entities, omit stable identifiers, and provide no durable record of consensus. That opacity creates coordination debt: collaborators cannot reliably resolve referents across turns, reconcile divergent framings without ad hoc bookkeeping, or reason about lifecycle status (draft versus validated versus forked) in a reproducible way. Meanwhile, discoveries that ought to remain organization- or scenario-scoped routinely risk being pasted into broader contexts unless access control is disciplined by convention alone.

Existing multi-agent tooling addresses parts of execution (plans, tools, memory stores) yet rarely proposes a lightweight *document lingua franca* that is human-readable *and* machine-checkable across agents. What is missing is a thin standard that anchors semantics in prose while binding scope, typed relations, and consensus transitions to the same artifact. Such a bridge should favor adoption: authors should edit normal Markdown workflows without standing up heavyweight knowledge graphs or bespoke schemas.

**ADL Lite (Agent Discovery Language, Lite)** is a Markdown-native surface for Structured Semantic Anchoring (SSA). Documents combine three layers already specified in our system description: **L1** YAML front matter carries identifiers, lifecycle status, confidence, and coarse scope policies; **L2** Markdown body hosts human-readable argumentation with explicit linking conventions; **L3** fenced `adl:*` blocks expose typed relations, evidence, and seals suitable for deterministic parsing and tooling. Alongside syntax, ADL Lite ships reference implementations—hybrid retrieval over hot/warm tiers, SSA validation including scope-aware access checks, consensus chains with fork primitives, and agent-facing tooling aligned with reproducible scripted simulations—as laid out in our paper outline and specification.

For **ESWC / ISWC** readers, the thesis is intentionally narrow: a **Markdown-native operational ontology** between plain notes and OWL-heavy stacks—human-readable authoring (Method E) plus a closed predicate registry and schema-guided L3 validation (Method D), RDF-like triples in fenced blocks without a triple-store runtime, and an optional Turtle export path. **Consensus chains** and scope ACL show that the same artifact can support auditable multi-agent workflows; they are not a new planner or MAS runtime. A scripted five-role harness (Discoverer, Reviewer, Skeptic, Merger, Librarian) supplies reproducible lifecycle smoke tests; the contract also complements tool transports (e.g., MCP) without replacing them.

> **What we claim / What we do NOT claim**
>
> | We claim | We do NOT claim |
> |----------|-----------------|
> | A deployable **operational ontology** layer (YAML registry, strict/opt-in validation, L3 triples in Markdown) suitable for agentic KG authoring | A new multi-agent orchestration framework or benchmark-leading discovery agent |
> | **Mechanistic** pilot evidence: L3-indexed retrieval gains on opaque-anchor queries (RQ3 ablation), scope denials under probe (RQ4), append-only consensus logs vs plain Markdown (RQ2) | Universal RQ1 clarity lift: **fair-plain Δ=0** on paired stripped L2; scenario-only RQ3 hit **Δ=0** |
> | Referent-clarity advantage vs **unstructured** plain-LLM notes under proxy judges (pooled ADL−plain ≈ **+1.5**, `n=15`) | Production AML performance, human inter-rater RQ1 (study **cancelled**), or OWL reasoning / automatic taxonomy induction |
> | Honest reporting of ablations, negative controls, and pilot scale | That strict ontology mode improves headline RQ metrics (registry conformance only at `n=5` examples) |

**Contributions (Phase 1 pilots, evidence-ordered).** (1) **Operational ontology middle layer** (Phase 2a–2b): closed predicate registry, schema-guided validation (Method D), agent introspection without OWL reasoners; (2) **Tri-layer Markdown contract** with SSA validation, L3 relation/evidence blocks, and scope ACL; (3) **Open-source reference toolkit** (`adl_lite` parser, validator, `ADLMemory`, consensus engine); (4) **Reproducible evaluation harness** and AML mini-corpus with fair-plain and unstructured baselines; (5) **Pilot metrics** with explicit limits—mechanistic wins (RQ2/3 L3-only/RQ4), unstructured-vs-ADL RQ1 signal, and reported nulls (fair-plain RQ1 Δ=0; scenario RQ3 Δ=0).

Our pilot empirical program is ordered for **Semantic Web** reviewers: **operational ontology** conformance and **L3-sensitive retrieval** lead; **scope ACL** and **lifecycle traceability** support multi-agent coordination claims; **referent clarity** (RQ1) is a secondary LLM-judge pilot with explicit fair-plain nulls. Numbers below match **`docs/experiments/RESULTS.md`** (`pilot_freeze`, 2026-05-24) and companion JSON artifacts.

- **Ontology (strict validation):** Does a closed predicate registry reject unknown L3 relations under `--strict` on curated examples, without claiming RQ headline lifts?
- **RQ3 (L3-sensitive retrieval):** Against TF-IDF fair-plain on the AML corpus (**25** queries, **`k = 10`**), does L3 indexing improve recall—and does uplift concentrate on **`q21`–`q25`** opaque-anchor probes vs **`q01`–`q20`** scenario queries?
- **RQ4 (scope isolation):** Do scope ACL probes deny illicit cross-scope reads (**99/99** denied, **0** leaks)?
- **RQ2 (lifecycle traceability):** Does ADL expose append-only consensus transitions on scripted multi-document workloads (**8** vs plain **0**), with MiMo single-discovery batches reported only under comparability caveats?
- **RQ1 (referent clarity, secondary):** Under LLM-as-judge on **`n = 15`**, does ADL beat **unstructured** plain-LLM notes while **fair-plain** paired controls show **Δ = 0**? Human inter-rater study **cancelled** (proxy judges only).

Readers should interpret this introduction as scaffolding for fuller related-work positioning (see **`docs/paper/RELATED_WORK.md`** and **`docs/paper/OUTLINE.md`**) and for an evaluation section that foregrounds pilots, proxies, and ablation splits rather than extrapolating to production workloads.

## 2. Related Work

ADL Lite sits at the intersection of multi-agent collaboration, lightweight knowledge structuring, and retrieval over mixed structured-unstructured corpora. It targets stronger semantic anchoring than plain Markdown with lower overhead than ontology-first systems.

### 2.1 Agent discovery and multi-agent knowledge coordination

Recent multi-agent systems have improved planning, tool use, and division of labor—planner–executor loops, debate-style review, and shared memory substrates (e.g., long-horizon agent memory in Park et al.'s generative agents and MemGPT-style context management). Tool transports such as MCP and agent-to-agent protocols standardize *invocation*, not the *shape* of durable discoveries. In practice, teams still persist agent outputs as conversational text or loosely formatted notes. That creates recurring coordination problems: unstable referents, implicit scope assumptions, and weak provenance for why a concept was accepted, forked, or deprecated.

ADL Lite contributes at the **document-contract** layer beneath orchestration. Instead of proposing a new runtime, it standardizes what a discovery artifact must contain so heterogeneous agents can parse, validate, and transition the same object—analogous to how interchange formats stabilized web APIs, but oriented to concept lifecycle and retrieval rather than RPC payloads.

### 2.2 Structured knowledge in Markdown

Markdown with YAML front matter is now common in static-site systems and technical knowledge bases. Front matter gives lightweight metadata without abandoning human-readable authoring. Wiki links similarly provide graph affordances in prose-centric documents. ADL Lite builds directly on these conventions.

The key extension is typed L3 blocks (`adl:relation`, `adl:evidence`, `adl:seal`) that formalize semantics usually left implicit in natural language. This mirrors RDF-like subject-predicate-object modeling at an author-editable level, without requiring full triple-store infrastructure.

By preserving normal Markdown ergonomics, ADL Lite reduces migration friction while still enabling deterministic parsing and validation.

### 2.3 Retrieval over structured versus plain text

Retrieval literature shows that explicit structure can improve ranking when queries target relational information that plain lexical overlap under-represents. At the same time, structure-aware methods may offer limited gains on straightforward scenario queries already well served by lexical retrieval.

The ADL Lite retrieval findings in Phase B follow this pattern. Under fair-plain comparisons, scenario-only subsets show small or near-zero hit-recall deltas, while L3-only opaque-anchor subsets account for most of the headline gap.

ADL Lite therefore does not claim that structure always dominates plain text retrieval; it supports the narrower claim that typed relational anchors matter most for relation-sensitive probes.

### 2.4 AML typology and transaction monitoring context

In anti-money-laundering (AML) and transaction monitoring domains, practitioners rely on typology-driven reasoning that is often documented in narrative reports and analyst notes. This creates a recurring challenge for automation: high-value insights may exist in text but remain difficult to query, compare, and lifecycle-manage.

ADL Lite is not an AML detection model and does not replace statistical monitoring pipelines. Its role is representational: to encode discovered patterns, evidence pointers, and relation links in a form that both humans and agents can process consistently.

By evaluating on an AML-oriented mini corpus, ADL Lite treats domain specificity as a stress test for document semantics rather than a claim of production-grade compliance performance.

### 2.5 Positioning: plain Markdown versus heavy ontologies

A useful way to locate ADL Lite is on a spectrum:

- At one end, **plain Markdown** maximizes author freedom but leaves semantics, lifecycle, and access policy mostly implicit.
- At the other, **heavy ontology stacks** maximize formal expressiveness and inferencing potential but often impose high modeling and infrastructure costs.

ADL Lite occupies a middle position with three practical commitments.

First, it remains **Markdown-native**. Authors do not leave familiar tooling; they add constrained metadata and typed blocks to ordinary documents.

Second, it enforces **minimal semantic discipline** through validators: scoped identifiers, status transitions, relation slot checks, and pronoun-policy constraints for referent clarity. This is stronger than best-effort conventions, but still lighter than full ontology governance.

Third, it supports **incremental retrieval enhancement**. Teams can run TF-IDF with relation-aware boosts from L3 today, and optionally layer hybrid embedding scorers later, without redesigning the document format.

This positioning matters for deployment realism. Many teams do not have resources to maintain enterprise knowledge graph stacks, yet still need more than unstructured notes.

### 2.6 Distinct contribution in context

Relative to prior strands, ADL Lite combines four elements in a single, low-friction artifact contract: (1) tri-layer Markdown representation, (2) SSA-oriented validation with referent and scope constraints, (3) consensus-chain lifecycle logging with fork support, and (4) hybrid memory indexing that integrates relational signal without requiring a heavyweight ontology runtime.

The resulting research proposition is intentionally bounded. ADL Lite argues that coordination benefits can emerge from disciplined document structure before full formal knowledge engineering overhead. This proposition is testable with ambiguity checks, transition traceability, retrieval ablations, and scope-leak probes.

### 2.7 LLM ontology construction methods (2025–2026 landscape)

Recent surveys of LLM-driven knowledge-graph and ontology pipelines identify five recurring strategies: **pipeline decomposition** (LLM orchestrates; RDF/OWL holds the world model), **clustering-driven** extraction, **two-phase generation** (extract then build hierarchy), **schema-guided extraction** (closed predicate/class registry in prompts), and **end-to-end prompting** (single-shot Markdown or triple drafts). A practical synthesis (Wang, 2026 — *Building Knowledge Graphs with LLMs: Five Methods Compared*) stresses that relation extraction remains the hardest step and that validation against a published schema should follow generative authoring rather than replace human-readable surfaces.

ADL Lite maps to this landscape deliberately:

| External method | ADL Lite mechanism |
|-----------------|-------------------|
| E — End-to-end prompting | `prompts/write_discovery.md`, L1/L2/L3 Markdown authoring |
| D — Schema-guided extraction | `adl_core_ontology.yaml`, `OntologyManager`, `ADLValidator(strict=True)` |
| Pipeline decomposition (lightweight) | Parser → ontology registry → validator → `ADLMemory` / consensus chain |

We do **not** embed OWL reasoners or automatic hierarchy induction at production scale. Phase 2 Milestones **2a–2c** ship the schema registry, strict predicate gate, and agent introspection (`adl_ontology_query`); optional Turtle export remains a Phase 3 track. See `docs/proposals/ONTOLOGY_MIDDLE_LAYER.md` for the E→D agent loop.

## 3. Method

This section describes the ADL Lite representation, validation and consensus machinery, retrieval setup, and evaluation protocols used for RQ1-RQ4. The objective is to preserve Markdown-first authoring while enabling deterministic parsing, scope-constrained access control, and auditable lifecycle transitions.

### 3.1 ADL document model: L1/L2/L3

ADL Lite uses a three-layer document structure specified in `docs/SPEC.md` and implemented in `adl_lite/parser.py` and `adl_lite/models.py`.

**L1 (YAML front matter)** provides machine-readable metadata: document type (`adl_type`), stable identifier (`adl_id`), lifecycle `status`, confidence and novelty fields, and `scope` policy. The parser enforces a typed schema for these fields and type-specific constraints (for example, required `mechanism` for `discovery` documents). The `scope` grammar (`public`, `private/<org>`, `user/<id>`, `shared/<collab>`) is used later by access validation and retrieval filtering.

**L2 (Markdown body)** is the author-facing narrative layer. It remains close to ordinary Markdown, but is interpreted under Structured Semantic Anchoring (SSA) checks that require explicit referents.

**L3 (typed fenced blocks)** uses `adl:*` code fences for structured assertions embedded in the same Markdown file. Current subtypes include relation blocks, evidence blocks, and seal blocks. In practice, L3 carries relation triples (`source`, `relation`, `target`), evidence references, and optional formal assertion metadata.

The design principle is separation without fragmentation: one file remains readable as a normal note while parsers can extract typed structures for indexing and validation.

### 3.2 Validator behavior and pronoun policy

Validation is implemented by `ADLValidator` (`adl_lite/validator.py`) and surfaced through both CLI and Python APIs. The validator checks:

1. **L1 schema and range constraints** (e.g., confidence and novelty in `[0, 1]`, valid scope pattern, required fields by type).
2. **L2 SSA constraints**, including a pronoun prohibition for ambiguous demonstratives and fuzzy referents.
3. **L3 semantic slot constraints**, including non-empty source/target fields and valid URI schemes for relation targets.

The pronoun policy is central to RQ1 framing. ADL Lite disallows demonstrative forms such as "this/that/it/these/those" (and Chinese equivalents listed in the spec) in discovery-definition prose where they can destabilize cross-agent coreference. The policy is not a style preference; it is an alignment constraint meant to reduce referent drift in multi-agent settings. Instead of pronouns, authors are expected to use explicit concept names or scoped `adl://` URIs.

Scope checks are integrated through `validate_scope_access(doc_scope, requester_scope)`, supporting deterministic RQ4 leakage probes.

### 3.3 Consensus chain and fork-aware lifecycle

Consensus state management is implemented in `adl_lite/consensus.py`. ADL Lite models concept evolution as a restricted transition graph over statuses (`provisional`, `validated`, `deprecated`, `forked`, `archived`). Valid transitions are intentionally narrow (e.g., no outgoing transitions from `archived`) to maintain lineage integrity.

Each transition appends an auditable record, producing a lifecycle trace for each `adl_id`. This is the method basis for RQ2.

Fork handling is first-class: when a skeptic disputes a mechanism interpretation, the workflow marks the original as `forked` and opens a new `adl_id` chain for the alternative.

### 3.4 ADLMemory indexing (hot/warm/cold)

`ADLMemory` (`adl_lite/memory.py`) uses a hybrid storage model described in the specification:

- **Hot layer**: in-memory concept skeletons keyed by `adl_id` for fast lookup.
- **Warm layer**: SQLite persistence for documents and relation edges, with graph-structured traversal support.
- **Cold layer**: file-archive concept retained in the architecture but deferred operationally in the current phase.

The method intent is to balance latency and reproducibility: hot memory supports agent-loop responsiveness, warm storage supports reruns and relational queries, and cold storage remains a future scaling path.

For RQ3 retrieval experiments, ADL indexing includes L2 text and L3 relational signal (including resolved targets), while plain baselines strip L3 relation information to enforce fair comparisons at the prose layer.

### 3.5 Phase B baselines and retrieval setup

Phase B evaluation uses multiple baselines.

#### 3.5.1 Fair-plain baseline

The fair-plain baseline removes ADL structural wrappers while preserving L2 wording (implemented in `experiments/baselines/fair_plain.py` and used by RQ1/RQ3 scripts).

#### 3.5.2 Plain-LLM unstructured baseline

An additional unstructured baseline uses plain Markdown discoveries produced without ADL slot constraints (`experiments/rq1_plain_discover.py`). Current artifacts include fixture-backed pooled scoring in the `plain_llm` summary path when live proxy reruns are blocked by missing keys.

#### 3.5.3 Retrieval scoring baselines

The default Phase B retriever is TF-IDF with relation-aware graph boost over ADL index content, compared against a fair-plain TF-IDF baseline (`tfidf_fair_plain`). The primary metric is recall@10 (hit and label variants). Phase B ablations split scenario queries (`q01-q20`) and L3-only opaque-anchor queries (`q21-q25`) in `docs/experiments/rq3_ablation.json`, showing where relation signal contributes most.

An optional hybrid scorer (`hybrid_fair_plain`) adds embedding signal to normalized TF-IDF + L3 boost (Phase B+).

### 3.6 LLM-as-judge protocol (RQ1)

RQ1 uses an LLM-as-judge protocol for referent clarity with two proxy judges. The orchestration is implemented in `experiments/rq1_llm_judge.py`, which:

1. Loads a shared rubric prompt (`prompts/judge_referent_clarity.md`).
2. Scores ADL L2 text and paired fair-plain text.
3. Optionally scores unstructured plain-LLM text when available.
4. Aggregates per-judge and cross-judge summaries into `docs/experiments/rq1_llm_judge_summary.json`.

The method defaults to Cursor-proxy judge labels (`openai_proxy`, `composer_proxy`) and records model tags in output metadata. The same script also documents a direct API path: OpenAI/Anthropic routing is enabled only when caller-side provider keys are configured (as described in the module docstring and reproduction notes), and otherwise runs can rely on committed proxy summaries.

Disagreement handling is explicit: entries above the configured inter-judge threshold are flagged in the summary.

### 3.7 Reproducibility protocol

Reproducibility is anchored in committed scripts and artifacts:

- Core pilot narratives and metrics: `docs/experiments/RESULTS.md`
- RQ3 ablations: `docs/experiments/rq3_ablation.json`
- RQ1 judge aggregates: `docs/experiments/rq1_llm_judge_summary.json`
- End-to-end rerun checklist: `docs/experiments/REPRODUCE.md`

The reproduction guide specifies command order for tests, Phase B generation, scripted pipeline run, RQ1 judge sweep, and example validation, so reported metrics can be regenerated from a clean checkout.

### 3.8 Five-agent scripted harness (coordination smoke test)

Multi-agent coordination is exercised without live LLM APIs via `experiments/harness.py` and `experiments/run_sim.py --scripted`. Five roles—**Discoverer**, **Reviewer**, **Skeptic**, **Merger**, and **Librarian**—follow `docs/AGENT_WORKFLOW.md`: register provisional discoveries, challenge mechanisms, fork on dispute, merge validated concepts into `ADLMemory`, and query related concepts under scope. This harness supplies RQ2's multi-document transition counts and end-to-end parse/validate/store demos; it is a **reproducibility anchor**, not a claim about optimal real-team workflows or LLM sample efficiency.

### 3.9 Operational ontology middle layer (Phase 2a–2b)

Beyond per-document SSA checks, ADL Lite adds a **Markdown-native operational ontology**—a project-local semantic contract above SQLite/NetworkX storage, not a triple-store runtime. The registry lives in `adl_lite/adl_core_ontology.yaml` and is loaded by `OntologyManager` (`adl_lite/ontology.py`). It centralizes:

1. **Predicate closure** — a closed core set (`isomorphic-to`, `specialisation-of`, `indexed-phrase`, …) used when strict validation is enabled.
2. **Status transition graph** — the same edges consumed by `ConsensusEngine`, avoiding drift between validator and lifecycle logic.
3. **Scope namespace grammar** — prefixes aligned with L1 `scope` and RQ4 ACL probes.

**Positioning.** We adopt Wang (2026) **Method D (schema-guided extraction)**: agents author human-readable Markdown (**Method E**) and validators reject unknown L3 predicates when `ADLValidator(strict=True)` or `adl-lite validate --strict` is set. Default mode remains permissive (`strict=False`) so LLM discoverers can iterate before predicate closure.

**Pilot evidence (honest scale).** On the curated `examples/` corpus (**n = 5**), strict validation passes with zero predicate errors; `tests/fixtures/invalid_predicate.md` fails as expected on unknown predicate `similar`. The scripted harness can log `strict_ontology: true` when `ADL_STRICT_ONTOLOGY=1`. We do **not** report corpus-wide invalid-predicate rates or RQ deltas for strict mode; agent introspection (`adl_ontology_query`, Milestone 2c) is implemented but not wired to RQ headline metrics.

## 4. Evaluation

This section reports Phase B pilots for **ESWC / ISWC** framing: **operational ontology** evidence and **L3-sensitive retrieval** lead; **scope ACL** and **consensus traceability** support coordination claims; **RQ1** LLM-as-judge clarity is secondary with **fair-plain Δ = 0**. All figures match **`docs/experiments/RESULTS.md`** (`pilot_freeze`, 2026-05-24), **`summary_phase_b.json`**, **`rq1_llm_judge_summary.json`**, **`rq2_llm_summary.json`**, **`rq3_ablation.json`**, and **Table 2** (`docs/paper/table2_results.md`). Standalone draft: **`docs/paper/draft_evaluation.md`**.

Retrieval cohorts split scenario **`q01`–`q20`** (**`n = 20`**) from L3-only opaque-anchor **`q21`–`q25`** (**`n = 5`**; **`rq3_ablation.json`**).

### 4.1 Evaluation design for Semantic Web venues

Semantic Web reviewers typically ask whether a representation is **machine-checkable**, **interoperable**, and **honest about ablations**. We therefore foreground: (1) **closed-registry strict validation** (Method D) on curated Markdown; (2) **retrieval gains tied to L3 relation anchors** with fair-plain and subset reporting; (3) **deterministic scope denial** under adversarial probes. Multi-agent **consensus chains** demonstrate auditable lifecycle logging but are not positioned as a new MAS runtime. **RQ1** uses proxy judges with explicit **fair-plain nulls**; human inter-rater RQ1 was **cancelled**—we do not report human means.

### 4.2 Setup and corpus

The AML mini corpus (**`data/aml/`**, **20** concepts; **`queries.json` v0.3**: **20** scenario + **5** L3 queries → **25** evaluations at **`k = 10`**) drives retrieval; Phase B bundles label **`phase: B`** (`summary_phase_b.json`, `generated_at` 2026-05-23). TF-IDF scores an ADL index (L2 + L3 + relation boosts) vs **fair plain** (L2 only; **`tfidf_fair_plain`**). Consensus uses **`experiments/rq2_consensus.py`** (scripted) plus optional MiMo batch (**`n_runs` = 10**, **`rq2_llm_summary.json`**). RQ1 combines a **25**-pair heuristic rubric with LLM-as-judge on **`n = 15`** discoveries (fair-plain + unstructured plain-LLM; Wave **6b** proxy artifact). Scope: **60** ACL probes.

### 4.3 Ontology strict-validation pilot (Phase 2a–2b)

**Primary SW-facing evidence** (independent of RQ1–RQ4 headline deltas):

| Check | Result |
|-------|--------|
| `adl-lite validate --strict examples/*.md` | **5/5 pass** |
| `adl-lite validate --strict tests/fixtures/invalid_predicate.md` | **FAIL** (unknown predicate `similar`; expected) |
| `ADL_STRICT_ONTOLOGY=1` scripted harness | Logs strict mode; **0** ontology errors on repo examples |

**Ontology ablation.** Strict mode is an **opt-in gate** over a **closed predicate registry**; default authoring stays permissive for LLM drafts. We do **not** claim strict validation improves RQ3 recall or RQ1 clarity—only registry conformance at pilot scale (**n = 5** curated files) plus agent introspection (`adl_ontology_query`, Milestone 2c). Invalid-L3 rejection on hallucinated predicates is qualitative via harness `ontology_errors` when strict is on.

### 4.4 RQ3 — L3-sensitive retrieval recall @10

- **Full set** (**`n = 25`**): hit recall **1.00** vs **0.80** fair plain (**Δ = +0.20**); label recall **0.90** vs **0.68** (**Δ = +0.22**).
- **Scenario** (**`q01`–`q20`**, **`n = 20`**): hit **Δ = +0.00**, label **Δ ≈ +0.05**.
- **L3-only** (**`q21`–`q25`**, **`n = 5`**): hit **Δ = +1.00**, label **Δ = +1.00**.

Headline **+0.20** full-set hit recall is **not** uniform: scenario queries saturate both rankers; opaque-anchor probes drive the gap because fair-plain indexing withholds L3 relation signal.

**Limitations (RQ3):** Lightweight TF-IDF ranker; optional hybrid embeddings preserve the same split. Cite aggregate deltas only with ablation rows.

### 4.5 RQ4 — Scope isolation

**`adl_leaks` = 0**; **`99/99`** cross-scope probes **denied** via **`validate_scope_access`**. **`baseline_leaks_uncontrolled` = 0** without symmetric plain-Markdown instrumentation.

**Limitations (RQ4):** Strongest claim is specification-consistent denial under probes—not a comparative leakage rate for unstructured notes.

### 4.6 RQ1 — Referent clarity (secondary; LLM-judge pilot)

**Heuristic rubric** (25 pairs): **`adl_mean_ambiguity` = 0.0**, **`plain_mean_ambiguity` = 0.0**, **`ambiguity_reduction_pct` = 0.0**.

**LLM-as-judge** (**`n = 15`**): mean ADL **4.0667** / **4.6000** (Judges A/B) vs fair-plain **identical** → **Δ = 0.0** per judge; **`mean_across_judges_adl`: 4.3333**.

**Unstructured plain-LLM:** means **2.667** / **3.000** → ADL−plain **+1.400** / **+1.600** (~**+1.500** pooled). **`plain_llm_judge_disagreement_count` = 0**; **1** ADL/fair-plain pairing with material judge disagreement.

**Human RQ1:** **cancelled** (2026-05-24) — no human inter-rater means; LLM-as-judge / proxy only.

**Limitations (RQ1):** Proxy judges only; fair-plain **Δ = 0** shows no measurable lift from structure alone on paired L2; unstructured contrast reflects baseline authoring, not universal SSA advantage.

### 4.7 RQ2 — Consensus lifecycle traceability (supporting)

**Scripted harness (primary):** **8** ADL transitions, **3** validated documents, **5** documents total; plain **`baseline_transitions` = 0** — append-only lifecycle evidence, not throughput optimality.

**MiMo batch (caveated):** **`n_runs` = 10**, mean **2.0** transitions/run (σ **0.0**), **`success_rate` = 1.0**, **`revised_rate` = 0.7**. **`delta_llm_minus_scripted` = −6.0** vs scripted total **8**: **apples-to-oranges** (single-discovery register→validate vs multi-document choreography).

**Limitations (RQ2):** Do not interpret **2.0** vs **8** as efficiency without redesigned workloads.

### 4.8 Summary

Phase B supports an **operational ontology** contribution: registry conformance (**5/5** strict examples), **L3-only** retrieval uplift (**Δ +1.00** on five probes), scope denial (**99/99**), and honest nulls (fair-plain RQ1 **Δ = 0**; scenario RQ3 hit **Δ = 0**). Referent-clarity gains vs **unstructured** plain-LLM are reported with proxy limits; consensus and scope evidence are **mechanistic** coordination pilots. Full ledger: **Table 2** (`docs/paper/table2_results.md`).

## 5. Discussion

**What the pilots actually show.** The strongest, most defensible claims are *mechanistic*: ADL artifacts admit append-only consensus logs (RQ2), enforce scope denials under adversarial probes (RQ4), and index L3 relations that change ranking on relation-targeted queries (RQ3 ablation). Referent-clarity gains (RQ1) appear when comparing ADL to **unstructured** plain-LLM prose, but vanish under **fair-plain** controls—implying that, for the current MiMo-generated corpus, measured clarity tracks authoring constraints and baseline generator behavior as much as any post-hoc structural wrapper.

**Negative results policy.** We report Δ=0 fair-plain judge means and scenario-only retrieval deltas explicitly. Omitting them would overstate ADL's universal advantage and mislead multi-agent practitioners evaluating adoption cost.

**Threats to external validity.** (i) AML concepts are minimal stubs, not operational typologies; (ii) LLM-as-judge and MiMo generation couple evaluation to model families; (iii) RQ2 scripted versus LLM batch counts are not like-for-like workloads; (iv) five L3-only queries drive headline RQ3 deltas. Phase 2 should expand query diversity, optional second judge providers, small human **spot-checks** (not the cancelled full inter-rater RQ1 arm), and SAR-adjacent material under governance review.

**Relation to agent platforms.** ADL Lite is intentionally **orthogonal** to orchestration frameworks: teams can adopt the document contract inside existing agent stacks via parse/validate/store tools (`adl_lite/tools.py`, optional `scripts/mcp_adl.py`) without migrating planners or memory products.

## 6. Conclusion

ADL Lite investigates whether a lightweight, Markdown-native standard can make multi-agent discovery artifacts more auditable, retrievable, and scope-safe without requiring ontology-heavy infrastructure. Across RQ1-RQ4, the pilot evidence supports a mixed but coherent picture. For RQ2, ADL documents expose explicit consensus lifecycle traces where plain Markdown has no native transition chain. For RQ4, scope ACL checks deny all probed cross-scope accesses in the current instrumentation. For RQ3, retrieval gains are present at full-set level, but ablation shows that most of the hit-recall gap is concentrated in L3-only query slices rather than scenario-only queries. For RQ1, ambiguity outcomes are nuanced: fair-plain pairings show no measurable ADL advantage in the current proxy-judge aggregate, while comparisons against unstructured plain-LLM notes indicate better ADL clarity under the same rubric.

These findings remain phase-scoped pilot evidence. Retrieval ablations depend on **`q21`-`q25`**, five relation-sensitive probes, so headline deltas should travel with subset annotations. Cursor-proxy adjudication hydrates unstructured baselines offline (Wave 6b artifact) but remains no substitute for human annotation. AML corpora and scripted harnesses privilege reproducibility over operational fidelity.

**ESWC / ISWC relevance.** ADL Lite targets teams who need **operational ontology** discipline—schema-guided L3 authoring, YAML registry introspection, optional Turtle export—without standing up OWL reasoners or enterprise triple stores. Empirical ordering matches reviewer expectations: **strict registry conformance** and **L3-only retrieval** first; **scope ACL** and **consensus traceability** as mechanistic coordination evidence; **RQ1** LLM-judge clarity secondary with **fair-plain Δ=0** (human RQ1 **cancelled**). Honest nulls (scenario RQ3 hit Δ=0) bound Phase 1 pilot claims.

Future work should prioritize three directions. First, move from synthetic or template-derived artifacts toward real suspicious activity reporting (SAR)-adjacent case material under appropriate governance constraints. Second, strengthen subjective evaluation with additional LLM judge providers and small human spot-checks on a subset of discoveries—without reviving the cancelled full inter-rater RQ1 protocol. Third, evaluate embedding-augmented retrieval at larger scale with stronger query diversity and statistical testing, while preserving the same fair-plain controls used in this phase. If these steps hold, ADL Lite would offer a practical middle-layer standard: more semantically reliable than plain Markdown and more deployable than heavyweight ontology pipelines for many multi-agent knowledge workflows.
