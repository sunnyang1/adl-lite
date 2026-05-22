# ADL Lite — Paper Outline (AAMAS 2027 target)

## Title (working)

**ADL Lite: Markdown-Native Agent Discovery Language for Multi-Agent Concept Consensus**

## Abstract (stub)

Multi-agent systems generate overlapping conceptual discoveries in unstructured prose, causing ambiguity, scope leakage, and fork chaos. ADL Lite embeds Structured Semantic Anchoring (SSA) in Markdown via L1 YAML, L2 prose, and L3 typed blocks, with a hybrid memory index and blockchain-isomorphic consensus chains. Pilot evaluation on a 20-concept AML dataset shows zero scope leaks and measurable ambiguity reduction vs plain Markdown baselines.

## 1. Introduction

- Problem: agents share discoveries as opaque Markdown
- Gap: no lightweight consensus + scope + relation standard
- Contribution: ADL Lite toolkit, 5-agent scripted harness, pilot RQ1–RQ4

## 2. Related Work

See [`RELATED_WORK.md`](RELATED_WORK.md).

## 3. Research Questions

| RQ | Question | Metric |
|----|----------|--------|
| RQ1 | Does SSA reduce referential ambiguity? | Pronoun / validation error rate |
| RQ2 | Does explicit consensus reduce rounds to validated? | Transition count |
| RQ3 | Do L3 relations improve retrieval? | Recall@10 |
| RQ4 | Does scope ACL prevent leakage? | Cross-scope leak count |

## 4. Method

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

## 6. Discussion

- Scripted sim as reproducibility anchor
- Negative results policy
- Deferred: Lean4 execution, FAISS ANN

## 7. Conclusion

ADL Lite demonstrates that Markdown-native SSA is sufficient for Phase 1 consensus and scope guarantees; semantic retrieval gains require warm-layer vectors (future work).

## Appendix

- CLI reference (`adl-lite --help`)
- Example documents (`examples/`)
- Repro commands from RESULTS.md
