# ADL Lite — Paper Outline (AAMAS 2027 target)

## Title (working)

**ADL Lite: Markdown-Native Agent Discovery Language for Multi-Agent Concept Consensus**

## Abstract (stub)

Multi-agent systems generate overlapping conceptual discoveries in unstructured prose, causing ambiguity, scope leakage, and fork chaos. ADL Lite embeds Structured Semantic Anchoring (SSA) in Markdown via L1 YAML, L2 prose, and L3 typed blocks, with a hybrid memory index and blockchain-isomorphic consensus chains. Phase B and post-v0.3.0 pilots show zero scope leaks, higher retrieval recall, and explicit lifecycle traces, while ambiguity gains are mixed under fair-plain pairings.

Draft abstract: [`draft_abstract.md`](draft_abstract.md). Full manuscript draft: [`DRAFT.md`](DRAFT.md).

## 1. Introduction

- Problem: agents share discoveries as opaque Markdown
- Gap: no lightweight consensus + scope + relation standard
- Contribution: ADL Lite toolkit, 5-agent scripted harness, pilot RQ1–RQ4

## 2. Related Work

Draft: [`draft_related_work.md`](draft_related_work.md).

## 3. Research Questions

| RQ | Question | Metric |
|----|----------|--------|
| RQ1 | Does SSA reduce referential ambiguity? | Pronoun / validation error rate |
| RQ2 | Does explicit consensus reduce rounds to validated? | Transition count |
| RQ3 | Do L3 relations improve retrieval? | Recall@10 |
| RQ4 | Does scope ACL prevent leakage? | Cross-scope leak count |

## 4. Method

Draft: [`draft_method.md`](draft_method.md).

### 4.1 Three-layer syntax (L1/L2/L3)

See `docs/SPEC.md` and [`FIGURES.md`](FIGURES.md).

### 4.2 Hybrid memory (Hot/Warm/Cold)

- Hot: `ConceptSkeleton` HashMap
- Warm: SQLite + NetworkX relation graph
- Cold: deferred (file archive)

### 4.3 Concept Consensus Chain

Status machine + fork resolution (merge / parallel / prune).

### 4.4 Five-agent workflow

Discoverer → Reviewer → Skeptic → Merger → Librarian (`docs/AGENT_WORKFLOW.md`).

## 5. Evaluation

- Dataset: `data/aml/` — 20 concepts, 15 queries
- Baselines: plain Markdown, YAML-only wiki
- Results: `docs/experiments/RESULTS.md` (**pilot numbers**)

### 5.1 RQ1 — Referential ambiguity

- **Claim:** ADL enforces high referent clarity, but post-v0.3.0 fair-plain comparisons do not show a measurable ADL-vs-plain gain.
- **Method:** Ran `experiments/rq1_ambiguity.py` on Phase B pairs and a post-v0.3.0 LLM-as-judge pass (`docs/experiments/rq1_llm_judge_summary.json`) over three MiMo-generated discoveries using a shared L2 rubric.
- **Key numbers:** Phase B ambiguity rubric: `adl_mean_ambiguity=0.0`, `plain_mean_ambiguity=0.0`, `ambiguity_reduction_pct=0.0` (`n_pairs=25`). LLM-as-judge: `n_discoveries=3`, mean ADL score `4.3333` for both judges, mean ADL-minus-plain `0.0`, disagreement count `0`.
- **Limitations:** Only `n=3` post-v0.3.0 discoveries were judged; the judge pass is LLM-as-judge (not human annotation), so it supports consistency checks rather than human-grounded quality claims.

### 5.2 RQ2 — Consensus transitions

- **Claim:** ADL records explicit consensus lifecycle steps, while plain Markdown has no transition chain.
- **Method:** Used scripted consensus simulation (`experiments/rq2_consensus.py`) and post-v0.3.0 MiMo batch runs summarized in `docs/experiments/rq2_llm_summary.json`.
- **Key numbers:** Scripted Phase B: `8` ADL transitions (`3` validated docs, `n_docs=5`) vs plain baseline `0`. LLM batch (`n=10`): mean transitions `2.0` (std `0.0`), success rate `1.0`, mean attempts `1.7`, revised rate `0.7`, delta vs scripted `-6.0`.
- **Limitations:** LLM runs reached only register+validate (`2` transitions) per single-discovery run, while scripted totals (`8`) aggregate a multi-document harness; these counts are not a direct like-for-like efficiency comparison.

### 5.3 RQ3 — Retrieval recall@10

- **Claim:** ADL retrieval outperforms fair plain overall, with gains concentrated in relation-aware query settings rather than base scenario-only queries.
- **Method:** Ran `experiments/rq3_retrieval.py` in Phase B at `k=10` for TF-IDF and hybrid scorers, then split metrics across scenario (`q01`-`q20`), L3-only (`q21`-`q25`), and full query sets.
- **Table 1 (hit recall@10 ablation):**

| Subset | Scorer | ADL recall | Plain | Delta |
|--------|--------|------------|-------|-------|
| Scenario (`q01`-`q20`, `n=20`) | TF-IDF | 1.00 | 1.00 | +0.00 |
| L3-only (`q21`-`q25`, `n=5`) | TF-IDF | 1.00 | 0.00 | +1.00 |
| Full (`n=25`) | TF-IDF | 1.00 | 0.80 | +0.20 |
| Scenario (`q01`-`q20`, `n=20`) | Hybrid | 1.00 | 1.00 | +0.00 |
| L3-only (`q21`-`q25`, `n=5`) | Hybrid | 1.00 | 0.00 | +1.00 |
| Full (`n=25`) | Hybrid | 1.00 | 0.80 | +0.20 |

- **Key numbers:** Label recall deltas mirror the same pattern: TF-IDF scenario `+0.05`, L3-only `+1.00`, full `+0.24`; Hybrid scenario `+0.0667`, L3-only `+1.00`, full `+0.2533`.
- **Limitations:** The full-set delta includes `q21`-`q25` L3-only opaque-anchor queries; scenario-only deltas are smaller, so reported overall gains should be read with that ablation split.
- **Ablation note:** `q01`-`q20` (scenario) captures base retrieval behavior, while `q21`-`q25` isolates L3-only signal that drives most of the hit-recall gap.

### 5.4 RQ4 — Scope leakage

- **Claim:** ADL scope ACL blocked all tested cross-scope accesses in the pilot.
- **Method:** Ran scope probes through `experiments/rq4_leakage.py` using `ADLValidator.validate_scope_access`.
- **Key numbers:** `adl_leaks=0`, `denied_access=60`, `probes=60` (60/60 denied).
- **Limitations:** Baseline leakage control is not equivalently instrumented (`baseline_leaks_uncontrolled=0` in summary JSON), so this result is strongest as an ADL safety smoke test rather than a strict comparative benchmark.

## 6. Discussion

- Scripted sim as reproducibility anchor
- Negative results policy
- Deferred: Lean4 execution, FAISS ANN

## 7. Conclusion

ADL Lite demonstrates that Markdown-native SSA is sufficient for Phase 1 consensus traceability and scope guarantees; retrieval gains are strongest when L3 relation signal is query-relevant, and ambiguity claims remain provisional pending larger human-rated studies.

Draft: [`draft_conclusion.md`](draft_conclusion.md).

## Appendix

- CLI reference (`adl-lite --help`)
- Example documents (`examples/`)
- Repro commands from RESULTS.md
