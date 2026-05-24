# ADL Lite: Agent Discovery Language for Multi-Agent Concept Consensus

Version note: Draft pack for `v0.3.3` (Wave 6b), consolidating abstract, introduction, related work, method, evaluation, discussion, and conclusion into one manuscript artifact.

Supporting artifacts:
- Results summary: [`docs/experiments/RESULTS.md`](../experiments/RESULTS.md)
- Table 2 roll-up: [`docs/paper/table2_results.md`](table2_results.md)
- Reproduction guide: [`docs/experiments/REPRODUCE.md`](../experiments/REPRODUCE.md)

---

## Abstract

Multi-agent discovery workflows still exchange insights as unstructured Markdown or chat logs, which obscures referents, lifecycle status, and access scope. **ADL Lite** is a Markdown-native document contract—L1 YAML metadata, L2 prose under Structured Semantic Anchoring (SSA), and L3 typed `adl:*` blocks—paired with validators, a hybrid memory index, an append-only concept consensus chain, and an **operational ontology** middle layer (closed predicate registry; opt-in strict validation). We report Phase B pilots on an AML mini-corpus (`n=20` concepts, `25` retrieval queries) using reproducible scripts and fair-plain baselines.

Against **unstructured** plain-LLM notes (`n=15`, Cursor-proxy judges), ADL L2 prose scores higher on referent clarity (mean ADL−plain ≈ **+1.5** on a 1–5 rubric); against **fair-plain** pairings that preserve the same wording minus ADL structure, judge means are **identical** (Δ=0), isolating the benefit of authoring discipline rather than lexical content alone. ADL records **8** scripted consensus transitions versus **0** for plain Markdown; retrieval at `k=10` improves on the full query set (hit recall **1.00** vs **0.80**, Δ**+0.20**) with gains concentrated in five L3-only probes (Δ**+1.00**) rather than twenty scenario queries (hit Δ**0.00**); scope ACL denies **60/60** cross-scope probes. We treat these as **pilot-limited** evidence: small samples, proxy adjudication, and synthetic AML stubs—not production AML or human-grounded benchmarks.

---

## 1. Introduction

When multiple agents converge on overlapping conceptual discoveries, they typically exchange unstructured prose—in practice, conversational logs and Markdown snippets that bury entities, omit stable identifiers, and provide no durable record of consensus. That opacity creates coordination debt: collaborators cannot reliably resolve referents across turns, reconcile divergent framings without ad hoc bookkeeping, or reason about lifecycle status (draft versus validated versus forked) in a reproducible way. Meanwhile, discoveries that ought to remain organization- or scenario-scoped routinely risk being pasted into broader contexts unless access control is disciplined by convention alone.

Existing multi-agent tooling addresses parts of execution (plans, tools, memory stores) yet rarely proposes a lightweight *document lingua franca* that is human-readable *and* machine-checkable across agents. What is missing is a thin standard that anchors semantics in prose while binding scope, typed relations, and consensus transitions to the same artifact. Such a bridge should favor adoption: authors should edit normal Markdown workflows without standing up heavyweight knowledge graphs or bespoke schemas.

**ADL Lite (Agent Discovery Language, Lite)** is a Markdown-native surface for Structured Semantic Anchoring (SSA). Documents combine three layers already specified in our system description: **L1** YAML front matter carries identifiers, lifecycle status, confidence, and coarse scope policies; **L2** Markdown body hosts human-readable argumentation with explicit linking conventions; **L3** fenced `adl:*` blocks expose typed relations, evidence, and seals suitable for deterministic parsing and tooling. Alongside syntax, ADL Lite ships reference implementations—hybrid retrieval over hot/warm tiers, SSA validation including scope-aware access checks, consensus chains with fork primitives, and agent-facing tooling aligned with reproducible scripted simulations—as laid out in our paper outline and specification.

For **AAMAS** readers, the central claim is not a new orchestration runtime but a **document contract** that heterogeneous agents can parse, validate, and lifecycle-manage consistently—complementary to tool transports (e.g., MCP) and planner-centric multi-agent frameworks. A scripted five-role harness (Discoverer, Reviewer, Skeptic, Merger, Librarian) exercises the contract without mandating a particular LLM provider.

**Contributions (Phase 1 pilots).** This paper contributes: (1) a normative tri-layer Markdown specification with SSA validation and scope ACL; (2) an open-source reference toolkit (`adl_lite` parser, validator, `ADLMemory`, consensus engine); (3) a reproducible evaluation harness and AML mini-corpus with fair-plain and unstructured baselines; (4) pilot evidence on four coordination properties—referent clarity, consensus traceability, relation-aware retrieval, and scope isolation—reported with explicit ablations and negative results where fair-plain controls erase apparent gains; and (5) an **operational ontology** middle layer (Phase 2a–2b) that centralizes predicate and transition registries for schema-guided authoring without OWL reasoners.

Our pilot empirical program asks whether this bundle improves properties that unstructured Markdown leaves implicit. Rather than asserting universal gains, we state four research questions and report numbers exactly as summarized in companion pilot artifacts (**`docs/experiments/summary_phase_b.json`**, **`docs/experiments/rq1_llm_judge_summary.json`**, **`docs/experiments/rq2_llm_summary.json`**, **`docs/experiments/RESULTS.md`**):

- **RQ1 (referential ambiguity):** When ADL-guided L2 prose is paired with fairness controls (stripped plain renderings matched to the same source) and-with an orthogonal unstructured baseline-with LLM-scored clarity, does referent tracking improve in measurable judge or rubric terms?
- **RQ2 (consensus traceability):** Does ADL expose explicit lifecycle transitions comparable to scripted multi-document workloads, relative to Markdown that lacks a chain? We contrast scripted harness aggregates with MiMo-batch single-discovery traces and discuss comparability explicitly.
- **RQ3 (retrieval):** Against a TF-IDF fair-plain baseline on the AML corpus, does indexing L3 relation signal improve recall @10-and how much of any gap concentrates on deliberately L3-aligned queries versus scenario-only subsets?
- **RQ4 (scope isolation):** Do scope ACL probes deny illicit cross-scope reads in the pilot instrumentation?

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

This section summarizes the Phase B pilot methodology and headline metrics for Research Questions **RQ1-RQ4**. All figures below appear in **`docs/experiments/summary_phase_b.json`**, **`docs/experiments/rq1_llm_judge_summary.json`**, **`docs/experiments/rq2_llm_summary.json`**, **`docs/experiments/rq3_ablation.json`**, and **`docs/paper/table2_results.md`**, alongside narrative exposition in **`docs/experiments/RESULTS.md`**.

Retrieval cohorts emphasize scenario queries **`q01`-`q20`** (**`n = 20`**) versus five **`q21`-`q25`** **L3-only** opaque-anchor probes that strip relational signal from baseline indexing (**`rq3_ablation.json`** freezes the splits).

### 4.1 Setup and corpus

Indexing and retrieval pilots run over the AML mini corpus under **`data/aml/`**, comprising **twenty concepts** assembled for controlled experiments (**`queries.json` v0.3 specifies twenty scenario-aligned queries plus five L3-anchor queries, totaling *n = 25* ranked evaluations at k = 10**). Phase B rerun outputs label the aggregate JSON as **`phase: B`** (`summary_phase_b.json`, `generated_at` 2026-05-23). Retrieval scoring uses TF-IDF on an ADL index that incorporates L2 and L3 material with relation-aware boosts, versus a **fair plain** baseline retaining L2 prose only (**`rq3_retrieval.scorer`: `tfidf_fair_plain`** in the Phase B bundle).

Consensus pilots pair a scripted five-document harness (**`experiments/rq2_consensus.py`**) against an optional MiMo-driven batch summarized post hoc (**n = 10** runs recorded in **`rq2_llm_summary.json`**).

Ambiguity pilots combine the Phase **B** heuristic ambiguity rubric on **twenty-five paired documents** (**`rq1_ambiguity.n_pairs`: 25** in `summary_phase_b.json`) with a separate **LLM-as-judge referent clarity** pass over **n = 15** MiMo-expanded discoveries (**`rq1_llm_judge_summary.json`**, `n_discoveries: 15`), including a **fair plain** comparator (paired stripped L2) and an unstructured **plain-LLM** track summarized under **`plain_llm`**. Wave **6b** adjudication uses committed Cursor-proxy artifacts (`data/eval/rq1_plain_llm_live_proxy_wave6b.json`) so unstructured baselines reproduce without OpenAI/Anthropic API keys.

Scope pilots issue **sixty validator probes**, all registering as denials (**`rq4_leakage`**: `denied_access: 60`, `probes: 60`, **`adl_leaks: 0`**).

### 4.2 RQ1 - Referential ambiguity

The Phase B ambiguity rubric reports symmetric means between ADL and fair plain (**`adl_mean_ambiguity` = 0.0**, **`plain_mean_ambiguity` = 0.0**) with **`ambiguity_reduction_pct` = 0.0**, underscoring that under these pairings neither side registers heuristic ambiguity signal.

Independent LLM-as-judge scores on **`n_discoveries: 15`** yield mean ADL clarity **4.0667** (strict proxy judge) versus **fair plain mean 4.0667**, and mean ADL clarity **4.6** versus **fair plain 4.6** (alternate proxy judge), producing **mean ADL - fair plain = 0.0** for both judges (**`fair_plain_comparison.adl_vs_plain_delta_mean`**). Aggregated judge means cite **mean_across_judges_adl: 4.3333**.

The unstructured **plain-LLM** arm—documented under **`plain_llm`**—reports slug-level unstructured writings averaging **2.667** (Judge A) / **3.000** (Judge B) pooled across **n = 15** rows, yielding mean ADL-minus-plain-LLM deltas **+1.400** and **+1.600** (~**+1.500** pooled). **`plain_llm_judge_disagreement_count`** is **0** after Wave 6b because adjudication attaches to reused slug prose bundles with small inter-judge spread. Across the fifteen ADL / fair-plain pairings adjudicators materially disagree once (`disagreement_count` **1**).

**Limitations (RQ1):** Sample size is bounded (**n = 15** judge pass; rubric **`n_pairs` = 25**). Judgments stem from Cursor-proxy LLM adjudication—not human labeling. Fair-plain Δ=0 shows that, for these MiMo outputs, SSA constraints do not add measurable clarity *beyond* the same stripped wording; gains versus unstructured plain-LLM reflect authoring discipline absent in the baseline generator.

### 4.3 RQ2 - Consensus transitions

The scripted Phase B harness records **eight ADL transitions** validating **three** documents across **five** total documents, while unstructured Markdown inherits **baseline_transitions = 0** (**`rq2_consensus`** in `summary_phase_b.json`). The MiMo consolidation batch (**`rq2_llm_summary.json`**, **`n_runs` = 10**) averages **`consensus_transitions.mean` = 2.0** (standard deviation **0.0**) with **`success_rate` = 1.0**, **`mean_attempts` = 1.7**, and **`revised_rate` = 0.7**. Matching the scripted aggregate transition count (**8**) yields **`delta_llm_minus_scripted` = -6.0**, highlighting scale mismatch rather than superiority.

**Limitations (RQ2):** The comparison is deliberately apples-to-oranges: scripted totals aggregate multi-document choreography, whereas MiMo batches follow single-discovery pipelines that mechanically cap near register-plus-validate flows (**two** transitions/run on average versus **eight** scripted). Efficiency claims thus require redesigned controlled workloads.

### 4.4 RQ3 - Retrieval recall @10

- Aggregate TF-IDF run (**`n_queries` = 25**): **hit recall 1.00** (ADL) versus **0.80** fair plain (**`delta` = +0.20**); label recall **0.9667** versus **0.7267** (**`label_recall_delta` ≈ +0.24**).
- Scenario-only cohort (**q01–q20**, **`scenario_n_queries` = 20**): **`scenario_hit_delta` = +0.00**, **`scenario_label_delta` ≈ +0.05**.
- L3-only cohort (**q21–q25**, **`n_queries` = 5**): **`delta` = +1.00**, **`label_recall_delta` = +1.00** (per **`rq3_ablation.json`**).

These splits demonstrate that headline recall deltas lean on **`q21`–`q25`**, the L3-only opaque-anchor bundle where relational signal is withheld from baseline indexing.

**Limitations (RQ3):** TF-IDF is a deliberately lightweight ranker; the dominating structural effect is relation visibility for the opaque-anchor cohort. Scenario-only hit recall shows no delta in this pilot—authors should not extrapolate full-corpus gains from aggregate metrics alone.

### 4.5 RQ4 - Scope leakage

The pilot emits **`adl_leaks` = 0** with **`60/60` probes denied** via **`validate_scope_access`**. Companion metadata flags **`baseline_leaks_uncontrolled` = 0** without comparable instrumentation parity.

**Limitations (RQ4):** Absence of a symmetric leakage probe on uninstrumented Markdown means the strongest headline is ADL behaving as intended under adversarial probing, not a controlled comparative leakage rate.

### 4.6 Ontology strict-validation pilot (Phase 2a–2b)

Independent of RQ1–RQ4 headline metrics, we report a **pilot conformance check** for the operational ontology layer:

- **`adl-lite validate --strict examples/*.md`:** **5/5 pass** on curated examples (all L3 predicates in registry).
- **`adl-lite validate --strict tests/fixtures/invalid_predicate.md`:** fails on unknown predicate `similar` (expected golden negative).
- **Harness flag:** `ADL_STRICT_ONTOLOGY=1 python -m experiments.run_sim --scripted` logs strict mode; invalid-L3 rejection ablation is qualitative (no RQ outcome lift claimed).

This is **pilot-scale registry evidence**, not a claim that strict mode improves RQ1–RQ4 outcomes. Agent-facing `adl_ontology_query` (Milestone 2c) ships in-tree.

In sum, Phase B aggregates show measurable retrieval uplift when L3 signal is opaque-anchor relevant, mechanically traceable consensus scaffolding, deterministic scope denial, and asymmetric referent clarity favoring ADL versus unstructured plain-LLM notes—surfaced via **Table 2** (`docs/paper/table2_results.md`)—while fair-plain controls and scenario-only retrieval splits temper universal performance claims.

## 5. Discussion

**What the pilots actually show.** The strongest, most defensible claims are *mechanistic*: ADL artifacts admit append-only consensus logs (RQ2), enforce scope denials under adversarial probes (RQ4), and index L3 relations that change ranking on relation-targeted queries (RQ3 ablation). Referent-clarity gains (RQ1) appear when comparing ADL to **unstructured** plain-LLM prose, but vanish under **fair-plain** controls—implying that, for the current MiMo-generated corpus, measured clarity tracks authoring constraints and baseline generator behavior as much as any post-hoc structural wrapper.

**Negative results policy.** We report Δ=0 fair-plain judge means and scenario-only retrieval deltas explicitly. Omitting them would overstate ADL's universal advantage and mislead multi-agent practitioners evaluating adoption cost.

**Threats to external validity.** (i) AML concepts are minimal stubs, not operational typologies; (ii) LLM-as-judge and MiMo generation couple evaluation to model families; (iii) RQ2 scripted versus LLM batch counts are not like-for-like workloads; (iv) five L3-only queries drive headline RQ3 deltas. Phase 2 should add human inter-rater studies (`data/eval/human_rq1_template.json` is scaffolded), larger query sets, and SAR-adjacent material under governance review.

**Relation to agent platforms.** ADL Lite is intentionally **orthogonal** to orchestration frameworks: teams can adopt the document contract inside existing agent stacks via parse/validate/store tools (`adl_lite/tools.py`, optional `scripts/mcp_adl.py`) without migrating planners or memory products.

## 6. Conclusion

ADL Lite investigates whether a lightweight, Markdown-native standard can make multi-agent discovery artifacts more auditable, retrievable, and scope-safe without requiring ontology-heavy infrastructure. Across RQ1-RQ4, the pilot evidence supports a mixed but coherent picture. For RQ2, ADL documents expose explicit consensus lifecycle traces where plain Markdown has no native transition chain. For RQ4, scope ACL checks deny all probed cross-scope accesses in the current instrumentation. For RQ3, retrieval gains are present at full-set level, but ablation shows that most of the hit-recall gap is concentrated in L3-only query slices rather than scenario-only queries. For RQ1, ambiguity outcomes are nuanced: fair-plain pairings show no measurable ADL advantage in the current proxy-judge aggregate, while comparisons against unstructured plain-LLM notes indicate better ADL clarity under the same rubric.

These findings remain phase-scoped pilot evidence. Retrieval ablations depend on **`q21`-`q25`**, five relation-sensitive probes, so headline deltas should travel with subset annotations. Cursor-proxy adjudication hydrates unstructured baselines offline (Wave 6b artifact) but remains no substitute for human annotation. AML corpora and scripted harnesses privilege reproducibility over operational fidelity.

**AAMAS relevance.** ADL Lite targets teams building **multi-agent knowledge workflows** who need audit trails and scope boundaries without adopting a full knowledge-graph stack. The strongest empirical signals today are **mechanistic** (consensus logs, ACL denials, L3 retrieval ablations) rather than end-to-end task success rates on open-ended discovery benchmarks—an honest scope boundary for Phase 1.

Future work should prioritize three directions. First, move from synthetic or template-derived artifacts toward real suspicious activity reporting (SAR)-adjacent case material under appropriate governance constraints. Second, add human spot-check and inter-rater validation loops for referent clarity and retrieval relevance so that RQ1 and RQ3 claims are less dependent on proxy judges. Third, evaluate embedding-augmented retrieval at larger scale with stronger query diversity and statistical testing, while preserving the same fair-plain controls used in this phase. If these steps hold, ADL Lite would offer a practical middle-layer standard: more semantically reliable than plain Markdown and more deployable than heavyweight ontology pipelines for many multi-agent knowledge workflows.
