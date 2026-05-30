# Evaluation (draft)

This section summarizes Phase B pilot methodology and headline metrics for **ESWC / ISWC** positioning: the **operational ontology** layer (closed predicate registry, schema-guided validation, L3 triples) and **mechanistic** pilots (L3-sensitive retrieval, scope ACL) lead; **multi-agent consensus** (RQ2) and **LLM-as-judge referent clarity** (RQ1) are supporting evidence with explicit null controls. Frozen numbers: **`docs/experiments/RESULTS.md`** (`pilot_freeze` block, 2026-05-24), **`docs/experiments/summary_phase_b.json`**, **`docs/experiments/rq1_llm_judge_summary.json`**, **`docs/experiments/rq2_llm_summary.json`**, **`docs/experiments/rq3_ablation.json`**, and **`docs/paper/table2_results.md`**.

Retrieval splits: scenario queries **`q01`–`q20`** (**`n = 20`**) versus five **`q21`–`q25`** **L3-only** opaque-anchor probes that withhold indexed-phrase relation signal from fair-plain indexing.

## Evaluation design for Semantic Web venues

Semantic Web reviewers typically ask whether a representation is **machine-checkable**, **interoperable**, and **honest about ablations**. Our Phase B program therefore foregrounds: (1) **registry conformance** under strict validation (Method D) on curated examples; (2) **retrieval sensitivity to L3 relation anchors** with fair-plain and scenario vs L3-only splits; (3) **deterministic scope denial** under adversarial probes. **RQ1** (referent clarity) uses proxy judges and reports **fair-plain Δ = 0** alongside unstructured plain-LLM contrasts. **Human RQ1 cancelled** (2026-05-24); `human_rq1.status: cancelled`, `n_rated: 0`. **RQ2** documents append-only lifecycle traces on scripted multi-document workloads; MiMo single-discovery batches are reported only with **apples-to-oranges** caveats (mean **2.0** transitions/run vs scripted **8** total).

## Setup and corpus

Indexing and retrieval pilots run over the AML mini corpus under **`data/aml/`** (**20** concepts; **`queries.json` v0.3** — **20** scenario-aligned queries plus **5** L3-anchor queries, **25** ranked evaluations at **`k = 10`**). Phase B aggregates label **`phase: B`** (`summary_phase_b.json`, `generated_at` 2026-05-23). Retrieval uses TF-IDF on an ADL index (L2 + L3 + relation-aware boosts) versus **fair plain** (L2 only; **`rq3_retrieval.scorer`: `tfidf_fair_plain`**).

Consensus pilots pair a scripted five-document harness (**`experiments/rq2_consensus.py`**) with an optional MiMo batch (**`n_runs` = 10** in **`rq2_llm_summary.json`**) summarized post hoc—not as a like-for-like efficiency benchmark.

Ambiguity pilots combine a Phase B heuristic rubric on **25** paired documents (**`rq1_ambiguity.n_pairs`: 25**) with LLM-as-judge referent clarity on **`n_discoveries` = 15** MiMo-expanded rows (**`rq1_llm_judge_summary.json`**), including fair-plain and unstructured **plain-LLM** arms (Wave 6b Cursor-proxy artifact when API keys are absent).

Scope pilots issue **99** cross-scope probes (33 indexed concepts × 3 requesters), all denied (**`rq4_leakage`**: `denied_access: 99`, `probes: 99`, **`adl_leaks: 0`**).

## Ontology strict-validation pilot (Phase 2a–2b) — primary SW evidence

Independent of RQ1–RQ4 headline deltas:

| Check | Result |
|-------|--------|
| `adl-lite validate --strict examples/*.md` | **5/5 pass** (closed predicate registry) |
| `adl-lite validate --strict tests/fixtures/invalid_predicate.md` | **FAIL (expected)** — unknown predicate `similar` |
| `ADL_STRICT_ONTOLOGY=1 python -m experiments.run_sim --scripted` | Harness logs strict mode; scripted corpus has **0** ontology errors |

**Ontology ablation (honest scope).** Strict mode is an **opt-in gate** (`ADLValidator(strict=True)` / `--strict`): default authoring stays permissive for LLM iteration. On curated **`examples/`** (**n = 5** files), strict validation is **5/5** pass; the golden negative fixture fails as intended. We do **not** claim strict mode improves RQ3 recall or RQ1 clarity—registry conformance and agent introspection (`adl_ontology_query`, Milestone 2c) are the pilot deliverables.

## RQ3 — L3-sensitive retrieval recall @10

- **Full set** (**`n_queries` = 25**): hit recall **1.00** (ADL) vs **0.80** fair plain (**Δ = +0.20**); label recall **0.90** vs **0.68** (**Δ = +0.22**).
- **Scenario-only** (**`q01`–`q20`**, **`n = 20`**): **`scenario_hit_delta` = +0.00**, **`scenario_label_delta` = +0.025**.
- **L3-only** (**`q21`–`q25`**, **`n = 5`**): hit **Δ = +1.00**, label **Δ = +1.00** (**`rq3_ablation.json`**).

Headline full-set gains concentrate on **opaque-anchor** probes where fair-plain indexing strips L3 relation signal; scenario queries already saturate both rankers at hit **1.00**.

**Limitations (RQ3):** TF-IDF is a lightweight ranker; optional hybrid embeddings reproduce the same split pattern. Do not cite **+0.20** without the ablation table.

## RQ4 — Scope isolation

**`adl_leaks` = 0**; **`99/99`** cross-scope probes **denied** via **`validate_scope_access`**. Companion metadata records **`baseline_leaks_uncontrolled` = 0** without symmetric Markdown instrumentation.

**Limitations (RQ4):** Strongest claim is ADL behaving as specified under probes—not a controlled comparative leakage rate for uninstrumented plain notes.

## RQ1 — Referent clarity (secondary; LLM-judge pilot)

**Heuristic rubric** (25 pairs): **`adl_mean_ambiguity` = 0.0**, **`plain_mean_ambiguity` = 0.0**, **`ambiguity_reduction_pct` = 0.0**.

**LLM-as-judge** (**`n = 15`**): mean ADL clarity **4.0667** / **4.6000** (Judges A/B) vs fair-plain **identical** → **`adl_vs_plain_delta_mean` = 0.0** per judge; **`mean_across_judges_adl`: 4.3333**.

**Unstructured plain-LLM** baseline: means **2.667** / **3.000** → ADL−plain **+1.400** / **+1.600** (~**+1.500** pooled). **`plain_llm_judge_disagreement_count` = 0** (slug-level prose reuse); **1** ADL/fair-plain pairing with \|Judge A − Judge B\| ≥ 2.

**Human RQ1:** **cancelled** — no human means reported; protocol retained for audit only.

**Limitations (RQ1):** Proxy adjudication only; fair-plain **Δ = 0** isolates structure-vs-wording for this corpus; unstructured gains reflect baseline generator discipline, not universal SSA lift.

## RQ2 — Consensus lifecycle traceability (supporting)

**Scripted harness (primary RQ2 evidence):** **8** ADL transitions, **3** documents validated, **5** documents total; plain Markdown **`baseline_transitions` = 0** — demonstrates append-only lifecycle logging, not sample efficiency.

**MiMo batch (caveated):** **`n_runs` = 10**, mean **`consensus_transitions` = 2.0** (σ = 0), **`success_rate` = 1.0**, **`revised_rate` = 0.7**. Versus scripted total **8**: **`delta_llm_minus_scripted` = −6.0** — **not** apples-to-oranges; single-discovery register→validate flows vs multi-document choreography.

**Limitations (RQ2):** Do not frame MiMo **2.0** vs scripted **8** as ADL being “worse” or “better”; redesign controlled workloads before efficiency claims.

---

**Summary.** Phase B supports an **operational ontology** story: strict registry conformance (**5/5** examples), L3-only retrieval uplift (**Δ +1.00** on five probes), and scope denial (**99/99**), with honest nulls on fair-plain RQ1 (**Δ = 0**) and scenario RQ3 hit recall (**Δ = 0**). Consolidated ledger: **Table 2** (`docs/paper/table2_results.md`).
