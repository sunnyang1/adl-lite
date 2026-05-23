# Evaluation (draft)

This section summarizes the Phase B pilot methodology and headline metrics for Research Questions **RQ1–RQ4**. All figures below appear in **`docs/experiments/summary_phase_b.json`**, **`docs/experiments/rq1_llm_judge_summary.json`**, **`docs/experiments/rq2_llm_summary.json`**, **`docs/experiments/rq3_ablation.json`**, and **`docs/paper/table2_results.md`** (combined Table 2 roll-up), with narrative exposition in **`docs/experiments/RESULTS.md`**. Retrieval splits follow scenario queries **`q01`–`q20`** (**`n = 20`**) versus five **`q21`–`q25`** anchors staged as **L3-only** opaque-anchor probes stripping indexed-phrase relation signal from fair-plain indexing.

## Setup and corpus

Indexing and retrieval pilots run over the AML mini corpus under **`data/aml/`**, comprising **twenty concepts** assembled for controlled experiments (**`queries.json` v0.3 specifies twenty scenario-aligned queries plus five L3-anchor queries, totaling *n = 25* ranked evaluations at k = 10**). Phase B rerun outputs label the aggregate JSON as **`phase: B`** (`summary_phase_b.json`, `generated_at` 2026-05-23). Retrieval scoring uses TF-IDF on an ADL index that incorporates L2 and L3 material with relation-aware boosts, versus a **fair plain** baseline retaining L2 prose only (**`rq3_retrieval.scorer`: `tfidf_fair_plain`** in the Phase B bundle).

Consensus pilots pair a scripted five-document harness (**`experiments/rq2_consensus.py`**) against an optional MiMo-driven batch summarized post hoc (**n = 10** runs recorded in **`rq2_llm_summary.json`**).

Ambiguity pilots combine the Phase **B** heuristic ambiguity rubric on **twenty-five paired documents** (**`rq1_ambiguity.n_pairs`: 25** in `summary_phase_b.json`; note `n_docs: 25` in the ambiguity block aligns with paired coverage) with a separate **LLM-as-judge referent clarity** pass over **n = 15** MiMo-expanded discoveries (**`rq1_llm_judge_summary.json`**, `n_discoveries: 15`), including a **fair plain** comparator (paired stripped L2) and an unstructured **plain-LLM** track summarized under **`plain_llm`**. **`plain_llm_fixture_merge_note`** records either Wave 6b live merges (`merge_plain_llm_live_scores`) or legacy demo fixtures, so reruns distinguish committed adjudication payloads without invoking OpenAI/Anthropic CLI keys when the Cursor-proxy JSON path is used.

Scope pilots issue **sixty validator probes**, all registering as denials (**`rq4_leakage`**: `denied_access: 60`, `probes: 60`, **`adl_leaks: 0`**).

## RQ1 — Referential ambiguity

The Phase B ambiguity rubric reports symmetric means between ADL and fair plain (**`adl_mean_ambiguity` = 0.0**, **`plain_mean_ambiguity` = 0.0**) with **`ambiguity_reduction_pct` = 0.0**, underscoring that under these pairings neither side registers heuristic ambiguity signal.

Independent LLM-as-judge scores on **`n_discoveries: 15`** yield mean ADL clarity **4.0667** (strict proxy judge) versus **fair plain mean 4.0667**, and mean ADL clarity **4.6** versus **fair plain 4.6** (alternate proxy judge), producing **mean ADL − fair plain = 0.0** for both judges (**`fair_plain_comparison.adl_vs_plain_delta_mean`**). Aggregated judge means cite **mean_across_judges_adl: 4.3333**.

The unstructured **plain-LLM** arm—documented under **`plain_llm`**—pools three MiMo unstructured writings (one AML slug scenario each) reused across all fifteen templated discoveries. Means on that baseline are **2.667** (Judge A) and **3.000** (Judge B) with pooled ADL − plain deltas **+1.400** and **+1.600** respectively (**≈ +1.500** averaging those judge-specific deltas); **`plain_llm_judge_disagreement_count`** falls to **0** because adjudication attaches to slug-level prose bundles where inter-judge spread stays beneath the disagreement threshold (**\|3 − 4\| < 2** after Wave 6b refresh). Across the fifteen ADL / fair-plain pairings adjudicators diverge materially on exactly **one** discovery (`disagreement_count` **1**).

**Limitations (RQ1):** Sample size is bounded (**n = 15** judge pass; rubric **`n_pairs` = 25**). Plain-LLM judgments remain proxy adjudication mediated through Cursor—not human-rated gold labels—although Wave 6b removes API-key gated fixture dependence for unstructured snapshots.

## RQ2 — Consensus transitions

The scripted Phase B harness records **eight ADL transitions** validating **three** documents across **five** total documents, while unstructured Markdown inherits **baseline_transitions = 0** (**`rq2_consensus`** in `summary_phase_b.json`). The MiMo consolidation batch (**`rq2_llm_summary.json`**, **`n_runs` = 10**) averages **`consensus_transitions.mean` = 2.0** (standard deviation **0.0**) with **`success_rate` = 1.0**, **`mean_attempts` = 1.7**, and **`revised_rate` = 0.7**. Matching the scripted aggregate transition count (**8**) yields **`delta_llm_minus_scripted` = −6.0**, highlighting scale mismatch rather than superiority.

**Limitations (RQ2):** The comparison is deliberately **apples-to-oranges**: scripted totals aggregate multi-document choreography, whereas MiMo batches follow single-discovery pipelines that mechanically cap near register-plus-validate flows (**two** transitions/run on average versus **eight** scripted). Efficiency claims thus require redesigned controlled workloads.

## RQ3 — Retrieval recall @10

Splits below mirror **`docs/experiments/rq3_ablation.json`** (frozen Phase B reruns) and **`table2_results.md`** formatting:

- Aggregate TF-IDF run (**`n_queries` = 25**): **hit recall 1.00** (ADL) versus **0.80** fair plain (**`delta` = +0.20**); label recall **0.9667** versus **0.7267** (**`label_recall_delta` ≈ +0.24**, matching **RESULTS.md** rounding).
- Scenario-only cohort (**q01–q20**, **`scenario_n_queries` = 20**): **`scenario_hit_delta` = +0.00**, **`scenario_label_delta` ≈ +0.05**.

These splits demonstrate that headline recall deltas lean on **`q21`–`q25`**, the L3-only opaque-anchor bundle where relational signal is withheld from baseline indexing.

**Limitations (RQ3):** TF-IDF is a deliberately lightweight ranker with optional heavier hybrid modes noted in **`RESULTS.md`** but not summarized here beyond the caveat that embeddings change absolute gaps; regardless, the dominating structural effect is relation visibility for the opaque-anchor cohort.

## RQ4 — Scope leakage

The pilot emits **`adl_leaks` = 0** with **`60/60` probes denied** via **`validate_scope_access`**. Companion metadata flags **`baseline_leaks_uncontrolled` = 0** without comparable instrumentation parity.

**Limitations (RQ4):** Absence of a symmetric leakage probe on uninstrumented Markdown means the strongest headline is ADL behaving as intended under adversarial probing, not a controlled comparative leakage rate.

---

In sum, the Phase B aggregates establish measurable retrieval uplift under explicit L3 signal, mechanically traceable consensus events, deterministic scope denial on curated probes, and mixed ambiguity outcomes depending on fairness controls—all documented with provenance cited above—including **Table 2** (`docs/paper/table2_results.md`) as a consolidated pilot ledger while acknowledging proxy adjudication workload heterogeneity across RQs pending larger human-rated studies.
