# Table 2 — Aggregated Phase B pilots (RQ1–RQ4)

Pilot metrics consolidated from **`docs/experiments/rq1_llm_judge_summary.json`**, **`docs/experiments/rq2_llm_summary.json`**, **`docs/experiments/rq3_ablation.json`**, **`docs/experiments/RESULTS.md`**, and **`docs/experiments/summary_phase_b.json`** (Phase B aggregates). Retrieval rows use **`k = 10`** hit recall; RQ3 “Plain” denotes the Phase B fair-plain baseline.

| RQ | Metric | ADL | Baseline | Δ | n |
|:--:|--------|:---:|:--------:|:-:|:-:|
| **RQ1** | Referent clarity score (Judge A, strict Cursor proxy vs unstructured plain‑LLM) | 4.067 | 2.667 | +1.400 | 15 |
| **RQ1** | Referent clarity score (Judge B, careful Cursor proxy vs unstructured plain‑LLM) | 4.600 | 3.000 | +1.600 | 15 |
| **RQ1** | Mean ADL − plain‑LLM (average of Judges A&B δ) | — | — | **+1.500** | 15 |
| **RQ1** | Referent clarity vs fair-plain (paired stripped L2; Judge A) | 4.067 | 4.067 | 0.000 | 15 |
| **RQ1** | Referent clarity vs fair-plain (Judge B) | 4.600 | 4.600 | 0.000 | 15 |
| **RQ2** | Consensus transitions — scripted Phase B harness | 8 | 0 (plain) | +8 | 5 docs |
| **RQ2** | Consensus transitions mean — MiMo batch vs scripted baseline | 2.0 | 8 (scripted) | −6.0 | 10 runs |
| **RQ3** | Hit recall @10 — TF-IDF — full queries | 1.00 | 0.80 | +0.20 | 25 |
| **RQ3** | Hit recall @10 — TF-IDF — scenario **`q01`–`q20`** only | 1.00 | 1.00 | +0.00 | 20 |
| **RQ3** | Hit recall @10 — TF-IDF — L3-only **`q21`–`q25`** only | 1.00 | 0.00 | +1.00 | 5 |
| **RQ3** | Label recall @10 — TF-IDF — full queries | 0.9667 | 0.7267 | +0.24 | 25 |
| **RQ3** | Label recall @10 — TF-IDF — scenario **`q01`–`q20`** | 0.9583 | 0.9083 | +0.05 | 20 |
| **RQ3** | Label recall @10 — TF-IDF — L3-only **`q21`–`q25`** | 1.0000 | 0.0000 | +1.00 | 5 |
| **RQ3** | Hit recall @10 — hybrid — full queries | 1.00 | 0.80 | +0.20 | 25 |
| **RQ3** | Hit recall @10 — hybrid — scenario **`q01`–`q20`** | 1.00 | 1.00 | +0.00 | 20 |
| **RQ3** | Hit recall @10 — hybrid — L3-only **`q21`–`q25`** | 1.00 | 0.00 | +1.00 | 5 |
| **RQ3** | Label recall @10 — hybrid — full queries | 0.9800 | 0.7267 | +0.2533 | 25 |
| **RQ3** | Label recall @10 — hybrid — scenario **`q01`–`q20`** | 0.9750 | 0.9083 | +0.0667 | 20 |
| **RQ3** | Label recall @10 — hybrid — L3-only **`q21`–`q25`** | 1.0000 | 0.0000 | +1.00 | 5 |
| **RQ4** | Cross-scope leakage count (validated pilot) | 0 leaks | baseline not instrumented | — | 60 probes |

Plain‑LLM RQ1 baselines recycle **three** MiMo unstructured writings (`experiments/outputs/plain_discovery_*.md`) across the fifteen templated discoveries; deltas use per-row pairing to each ADL path in **`human_rq1_template.json`**.

**Reproduce summarization:**

```bash
python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture
# or hydrate via:
python -m experiments.rq1_proxy_judge
```
