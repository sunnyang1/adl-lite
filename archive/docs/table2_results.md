# Table 2 — Aggregated Phase B pilots (evidence-ordered)

Pilot metrics for **ESWC / ISWC** narrative: **ontology strict validation** and **RQ3/RQ4** lead; **RQ1/RQ2** supporting. Sources: **`docs/experiments/RESULTS.md`** (`pilot_freeze` 2026-05-24), **`rq1_llm_judge_summary.json`**, **`rq2_llm_summary.json`**, **`rq3_ablation.json`**, **`summary_phase_b.json`**. Retrieval: **`k = 10`** hit recall unless noted; RQ3 “Plain” = Phase B fair-plain baseline.

## Ontology & mechanistic pilots (lead)

| RQ / track | Metric | ADL | Baseline | Δ | n |
|:--:|--------|:---:|:--------:|:-:|:-:|
| **Ontology** | `validate --strict` on `examples/*.md` | **5/5 pass** | — | — | 5 files |
| **Ontology** | `validate --strict` on `invalid_predicate.md` | **FAIL (expected)** | — | — | 1 fixture |
| **RQ3** | Hit recall @10 — TF-IDF — full queries | 1.00 | 0.80 | +0.20 | 25 |
| **RQ3** | Hit recall @10 — TF-IDF — scenario **`q01`–`q20`** | 1.00 | 1.00 | +0.00 | 20 |
| **RQ3** | Hit recall @10 — TF-IDF — L3-only **`q21`–`q25`** | 1.00 | 0.00 | +1.00 | 5 |
| **RQ3** | Label recall @10 — TF-IDF — full queries | 0.9000 | 0.6800 | +0.22 | 25 |
| **RQ3** | Label recall @10 — TF-IDF — scenario **`q01`–`q20`** | 0.8750 | 0.8500 | +0.025 | 20 |
| **RQ3** | Label recall @10 — TF-IDF — L3-only **`q21`–`q25`** | 1.0000 | 0.0000 | +1.00 | 5 |
| **RQ4** | Cross-scope leakage count | 0 leaks | baseline not instrumented | — | 99 probes |
| **RQ4** | Cross-scope probes denied | 99 denied | — | — | 99 probes |

## Hybrid retrieval (optional Phase B+)

| RQ | Metric | ADL | Plain | Δ | n |
|:--:|--------|:---:|:--------:|:-:|:-:|
| **RQ3** | Hit recall @10 — hybrid — full | 1.00 | 0.80 | +0.20 | 25 |
| **RQ3** | Hit recall @10 — hybrid — scenario **`q01`–`q20`** | 1.00 | 1.00 | +0.00 | 20 |
| **RQ3** | Hit recall @10 — hybrid — L3-only **`q21`–`q25`** | 1.00 | 0.00 | +1.00 | 5 |
| **RQ3** | Label recall @10 — hybrid — full | 0.9333 | 0.6800 | +0.2533 | 25 |
| **RQ3** | Label recall @10 — hybrid — scenario **`q01`–`q20`** | 0.9167 | 0.8500 | +0.0667 | 20 |
| **RQ3** | Label recall @10 — hybrid — L3-only **`q21`–`q25`** | 1.0000 | 0.0000 | +1.00 | 5 |

## RQ1 & RQ2 (supporting; caveats apply)

| RQ | Metric | ADL | Baseline | Δ | n |
|:--:|--------|:---:|:--------:|:-:|:-:|
| **RQ1** | Referent clarity (Judge A) vs **unstructured** plain-LLM | 4.067 | 2.667 | +1.400 | 15 |
| **RQ1** | Referent clarity (Judge B) vs **unstructured** plain-LLM | 4.600 | 3.000 | +1.600 | 15 |
| **RQ1** | Mean ADL − plain-LLM (avg of judge δ) | — | — | **+1.500** | 15 |
| **RQ1** | Referent clarity vs **fair-plain** (Judge A) | 4.067 | 4.067 | 0.000 | 15 |
| **RQ1** | Referent clarity vs **fair-plain** (Judge B) | 4.600 | 4.600 | 0.000 | 15 |
| **RQ1** | Human referent clarity | — | — | **cancelled** | 0 rated |
| **RQ2** | Consensus transitions — scripted harness | 8 | 0 (plain) | +8 | 5 docs |
| **RQ2** | Consensus transitions mean — MiMo batch | 2.0 | 8 (scripted total) | −6.0 | 10 runs |

Plain-LLM RQ1 baselines recycle **three** MiMo unstructured writings across **15** template rows; fair-plain uses paired stripped L2 (**Δ = 0**). MiMo **2.0** vs scripted **8** is **not** like-for-like (single-discovery vs multi-doc).

**Reproduce:**

```bash
python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture
adl-lite validate --strict examples/*.md
```
