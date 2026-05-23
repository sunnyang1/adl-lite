# ADL Lite: Agent Discovery Language for Multi-Agent Concept Consensus

Version note: Draft pack for `v0.3.3` (Wave 6a), consolidating introduction, related work, method, evaluation, and conclusion into one manuscript artifact.

Supporting artifacts:
- Results summary: [`docs/experiments/RESULTS.md`](../experiments/RESULTS.md)
- Reproduction guide: [`docs/experiments/REPRODUCE.md`](../experiments/REPRODUCE.md)

---

## 1. Introduction

When multiple agents converge on overlapping conceptual discoveries, they typically exchange unstructured prose-in practice, conversational logs and Markdown snippets that bury entities, omit stable identifiers, and provide no durable record of consensus. That opacity creates coordination debt: collaborators cannot reliably resolve referents across turns, reconcile divergent framings without ad hoc bookkeeping, or reason about lifecycle status (draft versus validated versus forked) in a reproducible way. Meanwhile, discoveries that ought to remain organization- or scenario-scoped routinely risk being pasted into broader contexts unless access control is disciplined by convention alone.

Existing multi-agent tooling addresses parts of execution (plans, tools, memory stores) yet rarely proposes a lightweight *document lingua franca* that is human-readable *and* machine-checkable across agents. What is missing is a thin standard that anchors semantics in prose while binding scope, typed relations, and consensus transitions to the same artifact. Such a bridge should favor adoption: authors should edit normal Markdown workflows without standing up heavyweight knowledge graphs or bespoke schemas.

**ADL Lite (Agent Discovery Language, Lite)** is a Markdown-native surface for Structured Semantic Anchoring (SSA). Documents combine three layers already specified in our system description: **L1** YAML front matter carries identifiers, lifecycle status, confidence, and coarse scope policies; **L2** Markdown body hosts human-readable argumentation with explicit linking conventions; **L3** fenced `adl:*` blocks expose typed relations, evidence, and seals suitable for deterministic parsing and tooling. Alongside syntax, ADL Lite ships reference implementations-hybrid retrieval over hot/warm tiers, SSA validation including scope-aware access checks, consensus chains with fork primitives, and agent-facing tooling aligned with reproducible scripted simulations-as laid out in our paper outline and specification.

Our pilot empirical program asks whether this bundle improves properties that unstructured Markdown leaves implicit. Rather than asserting universal gains, we state four research questions and report numbers exactly as summarized in companion pilot artifacts (**`docs/experiments/summary_phase_b.json`**, **`docs/experiments/rq1_llm_judge_summary.json`**, **`docs/experiments/rq2_llm_summary.json`**, **`docs/experiments/RESULTS.md`**):

- **RQ1 (referential ambiguity):** When ADL-guided L2 prose is paired with fairness controls (stripped plain renderings matched to the same source) and-with an orthogonal unstructured baseline-with LLM-scored clarity, does referent tracking improve in measurable judge or rubric terms?
- **RQ2 (consensus traceability):** Does ADL expose explicit lifecycle transitions comparable to scripted multi-document workloads, relative to Markdown that lacks a chain? We contrast scripted harness aggregates with MiMo-batch single-discovery traces and discuss comparability explicitly.
- **RQ3 (retrieval):** Against a TF-IDF fair-plain baseline on the AML corpus, does indexing L3 relation signal improve recall @10-and how much of any gap concentrates on deliberately L3-aligned queries versus scenario-only subsets?
- **RQ4 (scope isolation):** Do scope ACL probes deny illicit cross-scope reads in the pilot instrumentation?

Readers should interpret this introduction as scaffolding for fuller related-work positioning (see **`docs/paper/RELATED_WORK.md`** and **`docs/paper/OUTLINE.md`**) and for an evaluation section that foregrounds pilots, proxies, and ablation splits rather than extrapolating to production workloads.

## 2. Related Work

ADL Lite sits at the intersection of multi-agent collaboration, lightweight knowledge structuring, and retrieval over mixed structured-unstructured corpora. It targets stronger semantic anchoring than plain Markdown with lower overhead than ontology-first systems.

### 2.1 Agent discovery and multi-agent knowledge coordination

Recent multi-agent systems have improved planning, tool use, and division of labor, but many deployments still exchange discoveries as conversational text or loosely formatted notes. This creates recurring coordination problems: unstable referents, implicit scope assumptions, and weak provenance for why a concept was accepted, forked, or deprecated.

ADL Lite contributes at this document-contract layer. Instead of proposing a new runtime, it standardizes what a discovery artifact must contain so heterogeneous agents can parse, validate, and transition the same object.

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

## 4. Evaluation

This section summarizes the Phase B pilot methodology and headline metrics for Research Questions **RQ1-RQ4**. All figures below appear in **`docs/experiments/summary_phase_b.json`**, **`docs/experiments/rq1_llm_judge_summary.json`**, **`docs/experiments/rq2_llm_summary.json`**, **`docs/experiments/rq3_ablation.json`**, and **`docs/paper/table2_results.md`**, alongside narrative exposition in **`docs/experiments/RESULTS.md`**.

Retrieval cohorts emphasize scenario queries **`q01`-`q20`** (**`n = 20`**) versus five **`q21`-`q25`** **L3-only** opaque-anchor probes that strip relational signal from baseline indexing (**`rq3_ablation.json`** freezes the splits).

### 4.1 Setup and corpus

Indexing and retrieval pilots run over the AML mini corpus under **`data/aml/`**, comprising **twenty concepts** assembled for controlled experiments (**`queries.json` v0.3 specifies twenty scenario-aligned queries plus five L3-anchor queries, totaling *n = 25* ranked evaluations at k = 10**). Phase B rerun outputs label the aggregate JSON as **`phase: B`** (`summary_phase_b.json`, `generated_at` 2026-05-23). Retrieval scoring uses TF-IDF on an ADL index that incorporates L2 and L3 material with relation-aware boosts, versus a **fair plain** baseline retaining L2 prose only (**`rq3_retrieval.scorer`: `tfidf_fair_plain`** in the Phase B bundle).

Consensus pilots pair a scripted five-document harness (**`experiments/rq2_consensus.py`**) against an optional MiMo-driven batch summarized post hoc (**n = 10** runs recorded in **`rq2_llm_summary.json`**).

Ambiguity pilots combine the Phase **B** heuristic ambiguity rubric on **twenty-five paired documents** (**`rq1_ambiguity.n_pairs`: 25** in `summary_phase_b.json`; note `n_docs: 25` in the ambiguity block aligns with paired coverage) with a separate **LLM-as-judge referent clarity** pass over **n = 15** MiMo-expanded discoveries (**`rq1_llm_judge_summary.json`**, `n_discoveries: 15`), including a **fair plain** comparator (paired stripped L2) and an unstructured **plain-LLM** track summarized under **`plain_llm`**. **`plain_llm_fixture_merge_note`** records Wave 6b live merges (**`merge_plain_llm_live_scores`**) alongside optional legacy fixtures.

Scope pilots issue **sixty validator probes**, all registering as denials (**`rq4_leakage`**: `denied_access: 60`, `probes: 60`, **`adl_leaks: 0`**).

### 4.2 RQ1 - Referential ambiguity

The Phase B ambiguity rubric reports symmetric means between ADL and fair plain (**`adl_mean_ambiguity` = 0.0**, **`plain_mean_ambiguity` = 0.0**) with **`ambiguity_reduction_pct` = 0.0**, underscoring that under these pairings neither side registers heuristic ambiguity signal.

Independent LLM-as-judge scores on **`n_discoveries: 15`** yield mean ADL clarity **4.0667** (strict proxy judge) versus **fair plain mean 4.0667**, and mean ADL clarity **4.6** versus **fair plain 4.6** (alternate proxy judge), producing **mean ADL - fair plain = 0.0** for both judges (**`fair_plain_comparison.adl_vs_plain_delta_mean`**). Aggregated judge means cite **mean_across_judges_adl: 4.3333**.

The unstructured **plain-LLM** arm—documented under **`plain_llm`**—reports slug-level unstructured writings averaging **2.667** (Judge A) / **3.000** (Judge B) pooled across **n = 15** rows, yielding mean ADL-minus-plain-LLM deltas **+1.400** and **+1.600** (~**+1.500** pooled). **`plain_llm_judge_disagreement_count`** is **0** after Wave 6b because adjudication attaches to reused slug prose bundles with small inter-judge spread. Across the fifteen ADL / fair-plain pairings adjudicators materially disagree once (`disagreement_count` **1**).

**Limitations (RQ1):** Pilot scale stays small (**n = 15** judge pass versus rubric **`n_pairs` = 25**) and adjudication relies on proxies rather than human labels, albeit Wave 6b removes credential-gated merges for unstructured baselines.

### 4.3 RQ2 - Consensus transitions

The scripted Phase B harness records **eight ADL transitions** validating **three** documents across **five** total documents, while unstructured Markdown inherits **baseline_transitions = 0** (**`rq2_consensus`** in `summary_phase_b.json`). The MiMo consolidation batch (**`rq2_llm_summary.json`**, **`n_runs` = 10**) averages **`consensus_transitions.mean` = 2.0** (standard deviation **0.0**) with **`success_rate` = 1.0**, **`mean_attempts` = 1.7**, and **`revised_rate` = 0.7**. Matching the scripted aggregate transition count (**8**) yields **`delta_llm_minus_scripted` = -6.0**, highlighting scale mismatch rather than superiority.

**Limitations (RQ2):** The comparison is deliberately apples-to-oranges: scripted totals aggregate multi-document choreography, whereas MiMo batches follow single-discovery pipelines that mechanically cap near register-plus-validate flows (**two** transitions/run on average versus **eight** scripted). Efficiency claims thus require redesigned controlled workloads.

### 4.4 RQ3 - Retrieval recall @10

- Aggregate TF-IDF run (**`n_queries` = 25**): **hit recall 1.00** (ADL) versus **0.80** fair plain (**`delta` = +0.20**); label recall **0.9667** versus **0.7267** (**`label_recall_delta` = +0.24**).
- Scenario-only cohort (**q01-q20**, **`scenario_n_queries` = 20**): **`scenario_hit_delta` = +0.00**, **`scenario_label_delta` = +0.05**.
- L3-only cohort (**q21-q25**, **`n_queries` = 5**): **`delta` = +1.00**, **`label_recall_delta` = +1.00**.

These splits demonstrate that headline recall deltas lean on **q21-q25**, the L3-only opaque-anchor bundle where relational signal is withheld from baseline indexing.

**Limitations (RQ3):** The strongest retrieval lift depends on the five-query L3-only ablation subset; scenario-only hit recall shows no delta in this pilot.

### 4.5 RQ4 - Scope leakage

The pilot emits **`adl_leaks` = 0** with **`60/60` probes denied** via **`validate_scope_access`**. Companion metadata flags **`baseline_leaks_uncontrolled` = 0** without comparable instrumentation parity.

**Limitations (RQ4):** Absence of a symmetric leakage probe on uninstrumented Markdown means the strongest headline is ADL behaving as intended under adversarial probing, not a controlled comparative leakage rate.

In sum, Phase B aggregates show measurable retrieval uplift when L3 signal is opaque-anchor relevant, mechanically traceable consensus scaffolding, deterministic scope denial, and asymmetric referent clarity favors ADL versus pronoun-heavy unstructured snippets—surfaced succinctly via **Table 2** (`docs/paper/table2_results.md`)—without yet claiming statistically grounded production performance.

## 5. Conclusion

ADL Lite investigates whether a lightweight, Markdown-native standard can make multi-agent discovery artifacts more auditable, retrievable, and scope-safe without requiring ontology-heavy infrastructure. Across RQ1-RQ4, the pilot evidence supports a mixed but coherent picture. For RQ2, ADL documents expose explicit consensus lifecycle traces where plain Markdown has no native transition chain. For RQ4, scope ACL checks deny all probed cross-scope accesses in the current instrumentation. For RQ3, retrieval gains are present at full-set level, but ablation shows that most of the hit-recall gap is concentrated in L3-only query slices rather than scenario-only queries. For RQ1, ambiguity outcomes are nuanced: fair-plain pairings show no measurable ADL advantage in the current proxy-judge aggregate, while comparisons against unstructured plain-LLM notes indicate better ADL clarity under the same rubric.

These findings remain phase-scoped pilot evidence. Retrieval ablations depend on **`q21`-`q25`**, five relation-sensitive probes, so headline deltas should travel with subset annotations. Cursor-proxy adjudication now hydrates unstructured baselines offline (**Wave 6b** artifact) but remains no substitute for human annotation. AML corpora and scripted harnesses privilege reproducibility over operational fidelity.

Future work should prioritize three directions. First, move from synthetic or template-derived artifacts toward real suspicious activity reporting (SAR)-adjacent case material under appropriate governance constraints. Second, add human spot-check and inter-rater validation loops for referent clarity and retrieval relevance so that RQ1 and RQ3 claims are less dependent on proxy judges. Third, evaluate embedding-augmented retrieval at larger scale with stronger query diversity and statistical testing, while preserving the same fair-plain controls used in this phase. If these steps hold, ADL Lite would offer a practical middle-layer standard: more semantically reliable than plain Markdown and more deployable than heavyweight ontology pipelines for many multi-agent knowledge workflows.
