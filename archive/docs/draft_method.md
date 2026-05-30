# Method (draft)

This section describes the ADL Lite representation, validation and consensus machinery, retrieval setup, and evaluation protocols used for RQ1-RQ4. The objective is to preserve Markdown-first authoring while enabling deterministic parsing, scope-constrained access control, and auditable lifecycle transitions.

## 1. ADL document model: L1/L2/L3

ADL Lite uses a three-layer document structure specified in `docs/SPEC.md` and implemented in `adl_lite/parser.py` and `adl_lite/models.py`.

**L1 (YAML front matter)** provides machine-readable metadata: document type (`adl_type`), stable identifier (`adl_id`), lifecycle `status`, confidence and novelty fields, and `scope` policy. The parser enforces a typed schema for these fields and type-specific constraints (for example, required `mechanism` for `discovery` documents). The `scope` grammar (`public`, `private/<org>`, `user/<id>`, `shared/<collab>`) is used later by access validation and retrieval filtering.

**L2 (Markdown body)** is the author-facing narrative layer. It remains close to ordinary Markdown, but is interpreted under Structured Semantic Anchoring (SSA) checks that require explicit referents.

**L3 (typed fenced blocks)** uses `adl:*` code fences for structured assertions embedded in the same Markdown file. Current subtypes include relation blocks, evidence blocks, and seal blocks. In practice, L3 carries relation triples (`source`, `relation`, `target`), evidence references, and optional formal assertion metadata.

The design principle is separation without fragmentation: one file remains readable as a normal note while parsers can extract typed structures for indexing and validation.

## 2. Validator behavior and pronoun policy

Validation is implemented by `ADLValidator` (`adl_lite/validator.py`) and surfaced through both CLI and Python APIs. The validator checks:

1. **L1 schema and range constraints** (e.g., confidence and novelty in `[0, 1]`, valid scope pattern, required fields by type).
2. **L2 SSA constraints**, including a pronoun prohibition for ambiguous demonstratives and fuzzy referents.
3. **L3 semantic slot constraints**, including non-empty source/target fields and valid URI schemes for relation targets.

The pronoun policy is central to RQ1 framing. ADL Lite disallows demonstrative forms such as "this/that/it/these/those" (and Chinese equivalents listed in the spec) in discovery-definition prose where they can destabilize cross-agent coreference. The policy is not a style preference; it is an alignment constraint meant to reduce referent drift in multi-agent settings. Instead of pronouns, authors are expected to use explicit concept names or scoped `adl://` URIs.

Scope checks are integrated through `validate_scope_access(doc_scope, requester_scope)`, supporting deterministic RQ4 leakage probes.

## 3. Consensus chain and fork-aware lifecycle

Consensus state management is implemented in `adl_lite/consensus.py`. ADL Lite models concept evolution as a restricted transition graph over statuses (`provisional`, `validated`, `deprecated`, `forked`, `archived`). Valid transitions are intentionally narrow (e.g., no outgoing transitions from `archived`) to maintain lineage integrity.

Each transition appends an auditable record, producing a lifecycle trace for each `adl_id`. This is the method basis for RQ2.

Fork handling is first-class: when a skeptic disputes a mechanism interpretation, the workflow marks the original as `forked` and opens a new `adl_id` chain for the alternative.

## 4. ADLMemory indexing (hot/warm/cold)

`ADLMemory` (`adl_lite/memory.py`) uses a hybrid storage model described in the specification:

- **Hot layer**: in-memory concept skeletons keyed by `adl_id` for fast lookup.
- **Warm layer**: SQLite persistence for documents and relation edges, with graph-structured traversal support.
- **Cold layer**: file-archive concept retained in the architecture but deferred operationally in the current phase.

The method intent is to balance latency and reproducibility: hot memory supports agent-loop responsiveness, warm storage supports reruns and relational queries, and cold storage remains a future scaling path.

For RQ3 retrieval experiments, ADL indexing includes L2 text and L3 relational signal (including resolved targets), while plain baselines strip L3 relation information to enforce fair comparisons at the prose layer.

## 5. Phase B baselines and retrieval setup

Phase B evaluation uses multiple baselines.

### 5.1 Fair-plain baseline

The fair-plain baseline removes ADL structural wrappers while preserving L2 wording (implemented in `experiments/baselines/fair_plain.py` and used by RQ1/RQ3 scripts).

### 5.2 Plain-LLM unstructured baseline

An additional unstructured baseline uses plain Markdown discoveries produced without ADL slot constraints (`experiments/rq1_plain_discover.py`). Current artifacts include fixture-backed pooled scoring in the `plain_llm` summary path when live proxy reruns are blocked by missing keys.

### 5.3 Retrieval scoring baselines

The default Phase B retriever is TF-IDF with relation-aware graph boost over ADL index content, compared against a fair-plain TF-IDF baseline (`tfidf_fair_plain`). The primary metric is recall@10 (hit and label variants). Phase B ablations split scenario queries (`q01-q20`) and L3-only opaque-anchor queries (`q21-q25`) in `docs/experiments/rq3_ablation.json`, showing where relation signal contributes most.

An optional hybrid scorer (`hybrid_fair_plain`) adds embedding signal to normalized TF-IDF + L3 boost (Phase B+).

## 6. LLM-as-judge protocol (RQ1)

RQ1 uses an LLM-as-judge protocol for referent clarity with two proxy judges. The orchestration is implemented in `experiments/rq1_llm_judge.py`, which:

1. Loads a shared rubric prompt (`prompts/judge_referent_clarity.md`).
2. Scores ADL L2 text and paired fair-plain text.
3. Optionally scores unstructured plain-LLM text when available.
4. Aggregates per-judge and cross-judge summaries into `docs/experiments/rq1_llm_judge_summary.json`.

The method defaults to Cursor-proxy judge labels (`openai_proxy`, `composer_proxy`) and records model tags in output metadata. The same script also documents a direct API path: OpenAI/Anthropic routing is enabled only when caller-side provider keys are configured (as described in the module docstring and reproduction notes), and otherwise runs can rely on committed proxy summaries.

Disagreement handling is explicit: entries above the configured inter-judge threshold are flagged in the summary.

## 7. Reproducibility protocol

Reproducibility is anchored in committed scripts and artifacts:

- Core pilot narratives and metrics: `docs/experiments/RESULTS.md`
- RQ3 ablations: `docs/experiments/rq3_ablation.json`
- RQ1 judge aggregates: `docs/experiments/rq1_llm_judge_summary.json`
- End-to-end rerun checklist: `docs/experiments/REPRODUCE.md`

The reproduction guide specifies command order for tests, Phase B generation, scripted pipeline run, RQ1 judge sweep, and example validation, so reported metrics can be regenerated from a clean checkout.

## 8. Five-agent scripted harness (coordination smoke test)

Multi-agent coordination is exercised without live LLM APIs via `experiments/harness.py` and `experiments/run_sim.py --scripted`. Five roles—**Discoverer**, **Reviewer**, **Skeptic**, **Merger**, and **Librarian**—follow `docs/AGENT_WORKFLOW.md`: register provisional discoveries, challenge mechanisms, fork on dispute, merge validated concepts into `ADLMemory`, and query related concepts under scope. This harness supplies RQ2's multi-document transition counts and end-to-end parse/validate/store demos; it is a **reproducibility anchor**, not a claim about optimal real-team workflows or LLM sample efficiency.

## 9. Operational ontology middle layer (Phase 2a–2b)

Beyond per-document SSA checks, ADL Lite adds a **Markdown-native operational ontology**—a project-local semantic contract above SQLite/NetworkX storage, not a triple-store runtime. The registry lives in `adl_lite/adl_core_ontology.yaml` and is loaded by `OntologyManager` (`adl_lite/ontology.py`). It centralizes predicate closure, status transition graphs shared with `ConsensusEngine`, and scope namespace grammar.

We adopt Wang (2026) **Method D (schema-guided extraction)**: agents author human-readable Markdown (**Method E**) and validators reject unknown L3 predicates when `ADLValidator(strict=True)` or `adl-lite validate --strict` is set. Default mode remains permissive (`strict=False`) so LLM discoverers can iterate before predicate closure.

**Pilot evidence (honest scale).** On curated `examples/` (**n = 5**), strict validation passes; `tests/fixtures/invalid_predicate.md` fails on unknown predicate `similar`. Harness logging via `ADL_STRICT_ONTOLOGY=1` supports qualitative ablation. No RQ headline numbers are claimed for strict mode until Milestone 2c eval hooks ship.
