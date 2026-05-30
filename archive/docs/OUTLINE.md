# ADL Lite — Paper Outline (ESWC / ISWC 2027 primary; AAMAS 2027 backup)

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

- Dataset: `data/aml/` — 20 concepts, 25 queries @ k=10
- Baselines: plain Markdown fair-plain + unstructured MiMo stubs
- Results: **`docs/experiments/RESULTS.md`**, condensed **Table 2** in **`table2_results.md`** (paper folder)

### 5.1 RQ1 — Referential ambiguity

- **Claim:** Structured **ADL L2** aligns with fairness-stripped prose while retaining higher clarity than unstructured plain baselines laden with banned pronouns in this pilot snapshot.
- **Method:** Combine `experiments/rq1_ambiguity.py`, `human_rq1_template.json`, and `docs/experiments/rq1_llm_judge_summary.json`.
- **Key numbers (Wave 6b):** `n_discoveries=15`; fair-plain deltas `≈0` for paired judgings; unstructured plain pooled means **`2.667` / `3.000`** with ADL-plain deltas **`+1.400` / `+1.600` (~`+1.500` pooled)**; disagreement on ADL **1** ×15 pairing; unstructured judge disagreement **`0`** owing to reused slug adjudications.
- **Limitations:** Proxy adjudication substitutes for blind human labeling; unstructured writing sample count remains **three** prose bodies expanded across rows.

### 5.2 RQ2 — Consensus transitions

- **Claim:** ADL records explicit consensus lifecycle steps, while plain Markdown has no transition chain.
- **Method:** Used scripted consensus simulation (`experiments/rq2_consensus.py`) and post-v0.3.0 MiMo batch runs summarized in `docs/experiments/rq2_llm_summary.json`.
- **Key numbers:** Scripted Phase B: `8` ADL transitions (`3` validated docs, `n_docs=5`) vs plain baseline `0`. LLM batch (`n=10`): mean transitions `2.0` (std `0.0`), success rate `1.0`, mean attempts `1.7`, revised rate `0.7`, delta vs scripted `-6.0`.
- **Limitations:** LLM runs reached only register+validate (`2` transitions) per single-discovery run, while scripted totals (`8`) aggregate a multi-document harness; these counts are not a direct like-for-like efficiency comparison.

### 5.3 RQ3 — Retrieval recall@10

- **Claim:** ADL retrieval outperforms fair plain overall, with gains concentrated in relation-aware query settings rather than base scenario-only queries.
- **Method:** Ran `experiments/rq3_retrieval.py` in Phase B at `k=10` for TF-IDF and hybrid scorers, then split metrics across scenario (`q01`-`q20`), L3-only (`q21`-`q25`), and full query sets (see `docs/experiments/rq3_ablation.json` + **`table2_results.md`** alongside Table 1 here).
- **Table 1 (hit recall@10 ablation):**

| Subset | Scorer | ADL recall | Plain | Delta |
|--------|--------|------------|-------|-------|
| Scenario (`q01`-`q20`, `n=20`) | TF-IDF | 1.00 | 1.00 | +0.00 |
| L3-only (`q21`-`q25`, `n=5`) | TF-IDF | 1.00 | 0.00 | +1.00 |
| Full (`n=25`) | TF-IDF | 1.00 | 0.80 | +0.20 |
| Scenario (`q01`-`q20`, `n=20`) | Hybrid | 1.00 | 1.00 | +0.00 |
| L3-only (`q21`-`q25`, `n=5`) | Hybrid | 1.00 | 0.00 | +1.00 |
| Full (`n=25`) | Hybrid | 1.00 | 0.80 | +0.20 |

- **Key numbers:** Label recall deltas mirror the same pattern: TF-IDF scenario `+0.025`, L3-only `+1.00`, full `+0.22`; Hybrid scenario `+0.0667`, L3-only `+1.00`, full `+0.2533`.
- **Limitations:** The full-set delta includes `q21`-`q25` L3-only opaque-anchor queries; scenario-only deltas are smaller, so reported overall gains should be read with that ablation split.
- **Ablation note:** `q01`-`q20` (scenario) captures base retrieval behavior, while `q21`-`q25` isolates L3-only signal that drives most of the hit-recall gap.

### 5.4 RQ4 — Scope leakage

- **Claim:** ADL scope ACL blocked all tested cross-scope accesses in the pilot.
- **Method:** Ran scope probes through `experiments/rq4_leakage.py` using `ADLValidator.validate_scope_access`.
- **Key numbers:** `adl_leaks=0`, `denied_access=99`, `probes=99` (99/99 denied; 33 concepts × 3 requesters).
- **Limitations:** Baseline leakage control is not equivalently instrumented (`baseline_leaks_uncontrolled=0` in summary JSON), so this result is strongest as an ADL safety smoke test rather than a strict comparative benchmark.

## 6. Discussion

- Scripted sim as reproducibility anchor; five-agent roles as coordination smoke test
- Negative results policy: fair-plain Δ=0 (RQ1), scenario-only retrieval Δ=0 (RQ3)
- Threats: synthetic AML stubs, proxy judges, RQ2 workload mismatch, L3-only ablation slice
- Deferred: Lean4 seal execution, FAISS ANN, human inter-rater validation

Draft: [`draft_conclusion.md`](draft_conclusion.md) (includes AAMAS relevance paragraph).

## 7. Conclusion

ADL Lite demonstrates that Markdown-native operational ontology is sufficient for strict registry conformance, L3-sensitive retrieval, and scope guarantees; consensus chains provide mechanistic lifecycle evidence. RQ1 clarity uses LLM-as-judge with fair-plain **Δ=0**; human inter-rater RQ1 was **cancelled** (proxy judges only).

Draft: [`draft_conclusion.md`](draft_conclusion.md).

## Appendix

- CLI reference (`adl-lite --help`)
- Example documents (`examples/`)
- Repro commands from RESULTS.md
