# ADL Lite — Evaluation Results (Pilot)

> **Label:** All numbers below are **pilot / synthetic** metrics from the scripted simulation and token-overlap retrieval rubric. Re-run commands locally to reproduce.

## Pilot freeze (2026-05-24)

```yaml
frozen_at: 2026-05-24
pilot_freeze:
  rq1_llm_judge:
    n_discoveries: 15
    mean_adl_judge_a: 4.0667
    mean_adl_judge_b: 4.6000
    mean_fair_plain_delta: 0.0          # both judges; paired stripped L2
    mean_plain_llm_judge_a: 2.6667
    mean_plain_llm_judge_b: 3.0000
    mean_adl_minus_plain_llm: 1.5000   # pooled across judges
  rq2_scripted:
    adl_transitions: 8
    validated_count: 3
    plain_transitions: 0
  rq2_llm_batch:
    n_runs: 10
    mean_transitions: 2.0
    success_rate: 1.0
  rq3_tfidf:
    n_queries: 25
    hit_recall_adl: 1.00
    hit_recall_plain: 0.80
    hit_delta: 0.20
    label_recall_delta: 0.24
    scenario_hit_delta: 0.00            # q01-q20
    l3_only_hit_delta: 1.00           # q21-q25
  rq4_scope:
    leaks: 0
    probes_denied: 60
  ontology_strict:
    examples_pass: 5
    invalid_fixture_fails: true
  human_rq1:
    status: pending
    n_rated: 0
artifacts:
  - docs/experiments/summary_phase_b.json
  - docs/experiments/rq1_llm_judge_summary.json
  - docs/experiments/rq3_ablation.json
  - docs/experiments/rq1_human_summary.json
  - docs/paper/table2_results.md
reproduce: docs/experiments/RESEARCH_LOOP_CHECKLIST.md
```

> [!summary] Paper-ready summary (RQ1-RQ4)
> - **RQ1 (referent clarity vs unstructured plain‑LLM):** LLM‑as‑judge **`n=15`** shows pooled mean unstructured plain‑LLM clarity **2.667** (Judge A) / **3.000** (Judge B), mean ADL−plain **+1.400 / +1.600**, pooled between‑judge δ **+1.500** (**Wave 6b** Cursor‑proxy adjudication artifact `data/eval/rq1_plain_llm_live_proxy_wave6b.json`; no OPENAI_API_KEY required). Pairings vs fair‑plain stripped L2 stay **Δ=0**.
> - **RQ2 (consensus):** Scripted ADL chain logs `8` transitions (`3` validated docs, `n_docs=5`) vs plain `0`; post‑v0.3.0 MiMo batch (`n=10`) averages `2.0` transitions/run (std `0.0`, success `100%`, revised `70%`), `-6.0` vs scripted total.
> - **RQ3 (retrieval):** Phase B TF-IDF and hybrid both reach full-set hit recall `1.00` vs `0.80` (`+0.20`), but Table 1 ablation shows this gap is concentrated in `q21-q25` L3-only queries (`+1.00`) while scenario-only `q01-q20` hit delta stays `+0.00`; see `docs/experiments/rq3_ablation.json`.
> - **RQ4 (scope):** Scope ACL shows `0` leaks with `60/60` cross-scope probes denied.
> - **Reproduce (one line):** `pytest tests/ -v && python -m experiments.run_phase_b && ./scripts/demo_pipeline.sh --scripted && python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture`

## Phase B summary (v0.3.0)

| RQ | Metric | ADL / Phase B | Baseline | Δ / status |
|----|--------|---------------|----------|------------|
| **RQ1** | Pilot ambiguity reduction | ~100% (rubric) | fair plain paired | Pilot complete |
| **RQ1** | Human eval scaffold | `experiments/rq1_human_eval.py` + `docs/experiments/HUMAN_RQ1_PROTOCOL.md` | — | **Protocol ready** (ratings pending) |
| **RQ1** | LLM-as-judge (Cursor proxy, no user API keys) | `data/eval/human_rq1_template.json`, `docs/experiments/rq1_llm_judge_summary.json` | — | **Scored** n=15; **fair-plain Δ=0** (paired stripped L2 identical to ADL wording); plain‑LLM means **2.667 / 3.000**; ADL−plain Δ **+1.40 / +1.60** (**Wave 6b** live adjudication artifact) |
| **RQ2** | Scripted consensus transitions | 8 (3 validated) | 0 (plain) | +8 vs plain |
| **RQ2** | LLM batch (MiMo, n=10) | mean transitions **2.0** (σ=0), success **100%**, mean attempts **1.7**, revised **70%** | scripted 8 | Δ **−6.0** vs scripted; see `rq2_llm_summary.json` |
| **RQ3** | Hit recall @10 (TF-IDF, n=25) | **1.00** | 0.80 fair plain | **+0.20** |
| **RQ3** | Label recall @10 (TF-IDF) | **0.97** | 0.73 | **+0.24** |
| **RQ3** | Scenario q01–q20 (hybrid) | hit Δ **+0.00**, label Δ **+0.07** | fair plain | Phase B+ optional |
| **RQ4** | Scope leaks | **0** | uncontrolled baseline | 60/60 probes denied |

**LLM sim smoke (2026-05-23):** `python -m experiments.run_sim --llm` → `status: completed`, 1 attempt, 2 consensus transitions to `validated` (when API configured).

**RQ2 LLM batch (2026-05-23, MiMo n=10):** `python -m experiments.rq2_llm_batch --n 10` → 10/10 completed, mean **2.0** consensus transitions per discovery (register + validate), **70%** required one revision pass, vs scripted multi-doc baseline **8** transitions across 5 example docs.

**End-to-end demo:**

```bash
./scripts/demo_pipeline.sh --scripted
# or: python scripts/demo_pipeline.py --scripted
```



## Reproduce

```bash
cd adl-lite
pip install -e ".[dev]"

# Core smoke
pytest tests/ -v
adl-lite validate examples/*.md

# Scripted 5-agent sim
python -m experiments.run_sim --scripted

# Phase B evaluation pack
python -m experiments.run_phase_b

# All RQ pilots
python -m experiments.run_all

# End-to-end demo (validate → store → related)
./scripts/demo_pipeline.sh --scripted
```

Output: `docs/experiments/summary.json` (generated by `run_all`).

## ADL vs baseline comparison (pilot)

| Metric | ADL Lite | Plain Markdown baseline | Notes |
|--------|----------|-------------------------|-------|
| RQ1 pronoun rate | ~0.0% on validated examples | ~3–5% (synthetic inflated plain) | Lower = less ambiguity |
| RQ1 ambiguity reduction | **~100% pilot** | — | See `rq1_ambiguity.py` |
| RQ2 consensus transitions | **2×N** recorded | 0 (no chain) | N = example docs |
| RQ3 Recall@10 | **≥ plain** | token overlap only | Graph edges boost ADL |
| RQ4 scope leaks | **0** | uncontrolled reads | ACL enforced |

Run `python -m experiments.run_all` for exact pilot numbers on your machine.

## Research questions

### RQ1 — Ambiguity reduction

Structured slots + pronoun ban reduce fuzzy referents in L2 prose.

- Script: `experiments/rq1_ambiguity.py`
- Pilot compares ADL examples vs synthetic plain text with injected pronouns

**MiMo batch discovery:** `python -m experiments.rq1_batch_discover` — expand with **`--target-complete 15`** (rotates peripheral-trap → smurfing → crypto-mixer across empty template rows; **`--max-retries 2`** recommended).

**Plain unstructured baseline (Wave 4a + Wave 6b proxy):** `python -m experiments.rq1_plain_discover [--stub]` — writes **`experiments/outputs/plain_discovery_*.md`** (gitignored artifacts). Hydrate unstructured plain‑LLM scores without API keys via `python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture`, or **`python -m experiments.rq1_proxy_judge`** (bundled adjudication artifact `data/eval/rq1_plain_llm_live_proxy_wave6b.json`). For reproducing Wave 6a demo ints only, `-plain-fixture experiments/fixtures/plain_llm_judge_scores_demo.json` remains available.

| Item | Value |
|------|-------|
| Provider | Xiaomi MiMo Token Plan CN (`mimo-v2.5-pro` @ `token-plan-cn.xiaomimimo.com`) |
| Scenarios | 3 AML topic templates, expanded to **15** discoveries (canonical 3 + `*_batch*.md`) |
| Validator pass | **15/15** (100%) on Track B pilot run (**2026-05-23** UTC) |
| Outputs | Structured: `experiments/outputs/llm_discovery_{peripheral-trap,smurfing-pattern,crypto-mixer}.md` plus batches; Plain: **`plain_discovery_*.md`** (see Wave 4a command above) |
| Template | `data/eval/human_rq1_template.json` includes `discovery_path`, `validator_pass`, `plain_discovery_path`, LLM-as-judge fields |
| Human ratings | **Pending** (`referent_clarity` null; see `docs/experiments/HUMAN_RQ1_PROTOCOL.md`, then `python -m experiments.rq1_human_eval`) |

**LLM-as-judge referent clarity (Cursor proxy, no user API keys):** judge pass completed manually using the same rubric prompt with two independent proxy lenses.

| Item | Value |
|------|-------|
| Prompt | `prompts/judge_referent_clarity.md` (1–5 referent clarity, L2 only) |
| Judges | Judge A: `gpt-5.3-codex (cursor-proxy)` (strict entity resolution), Judge B: `composer-2-fast (cursor-proxy)` (careful referent tracing) |
| Claude status | Skipped (model unavailable in current region) |
| Discoveries | **n=15** MiMo outputs (canonical + batch-expanded rows on the human template) |
| Fair plain | Paired L2 via `adl_to_fair_plain` on the same discovery paths (identical wording to stripped L2 for these parses → Δ ≈ **0**) |
| Plain LLM | **Baseline:** three unstructured AML notes (`prompts/write_discovery_plain.md`; generator `experiments/rq1_plain_discover.py`). Rows share the slug‑matched **`plain_discovery_*.md`** file (**one prose sample per AML topic** reused across batch rows). **Wave 6b** replaces demo fixtures via `merge_plain_llm_live_scores()` / `--proxy-only` using `data/eval/rq1_plain_llm_live_proxy_wave6b.json` (**no judge API keys**). |
| Output | `docs/experiments/rq1_llm_judge_summary.json`; scores on template in `llm_judge_*` (+ `_plain`, `*_plain_llm`) slots |
| Disagreement | Flag when \|Judge A − Judge B\| ≥ 2 on ADL (**n=1** pilot). On the unstructured **`plain_llm`** strand (**Wave 6b**, three slug‑level prose samples reused ×15 rows) **`plain_llm_judge_disagreement_count` = 0** because intra‑slug judge spreads stay below threshold 2 (**\|3−4\| = 1** on crypto‑mixer). |

Proxy scores (**rq1_llm_judge_summary.json**, **Wave 6b** refreshed): judge means on ADL (**n=15**) **4.067** (Judge A) / **4.600** (Judge B); fair‑plain controls remain pairwise identical to stripped **L2** (**Δ≈0** vs fair plain). Mean unstructured plain‑LLM clarity **2.667** / **3.000** respectively; pooled mean ADL−plain **+1.400** / **+1.600**; averaged between judges **≈ +1.500**. Regenerate summaries with **`python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture`**. Table packaging: **`docs/paper/table2_results.md`** aggregates RQ1–RQ4 pilots.

Retries (expand run): peripheral-trap batch rows often took **2** attempts (one revision cycle); crypto-mixer batches were mostly **1** attempt; canonical crypto-mixer (2026-05-23) needed L2 rephrase for validator pronoun heuristic.

### RQ2 — Consensus rounds

ADL records explicit transitions; plain Markdown has no lifecycle chain.

- Script: `experiments/rq2_consensus.py`
- Metric: count of `ConsensusEntry` append operations to reach `validated`
- **Scripted baseline:** 8 transitions (3 docs validated, 5 docs total)
- **LLM batch (MiMo `mimo-v2.5-pro`, n=10):** mean **2.0** transitions/run (σ=0), **100%** success, **1.7** mean attempts, **70%** revised — single-discovery sim vs multi-doc scripted harness; see `docs/experiments/rq2_llm_summary.json`

### RQ3 — Retrieval Recall@10

15 AML queries against 20-concept index (`data/aml/`).

- Script: `experiments/rq3_retrieval.py`
- ADL index uses L3 relation count as tie-break boost; plain baseline strips L3

### RQ4 — Scope leakage

Probe cross-scope reads with `ADLValidator.validate_scope_access`.

- Script: `experiments/rq4_leakage.py`
- Target: **0 leaks** for ADL (deny by default on private scope)

## Scripted simulation log

```bash
python -m experiments.run_sim --scripted
# → experiments/logs/run_001.jsonl
```

Sample event:

```json
{"action": "transition", "adl_id": "disc-capital-trap", "role": "reviewer", "to": "validated"}
```

## LLM discovery simulation (optional)

End-to-end discoverer + reviewer using structured prompts, parse/validate, and auto-retry on failure.

```bash
pip install -e ".[dev,experiments]"
cp .env.example .env   # fill MIMO_API_KEY or OPENAI_API_KEY

# Xiaomi MiMo Token Plan (tp- keys, CN cluster default)
python -m experiments.run_sim --llm --max-retries 1

# Scripted baseline (no API)
python -m experiments.run_sim --scripted
```

| Item | Location |
|------|----------|
| Discovery output | `experiments/outputs/llm_discovery_<timestamp>.md` |
| Event log | `experiments/logs/llm_run.jsonl` |
| System prompt | `prompts/write_discovery.md` |

**Providers (first match):** MiMo (`MIMO_API_KEY`, `MIMO_API_BASE_URL`, `MIMO_MODEL`) then OpenAI (`OPENAI_API_KEY`).

**Validator (RQ1):** Blocks demonstrative/vague referents (`This shows…`, `because it`, Chinese pronouns). Allows grammatical **relative** `that` (e.g. `nodes that feed into…`).

**Smoke status (2026-05-23):** `run_sim --llm` → `status: completed`, 1 attempt, 2 consensus transitions to `validated`.

**Batch (2026-05-23):** `python -m experiments.rq2_llm_batch --n 10` with MiMo Token Plan CN — provider `mimo:mimo-v2.5-pro@https://token-plan-cn.xiaomimimo.com/v1`; 10/10 completed, 0 failures.

## Phase B RQ3 (TF-IDF + L3 graph boost)

```bash
python -m experiments.run_phase_b
# or: python -m experiments.rq3_retrieval --mode phase_b -k 10
```

| Metric @10 (n=25) | ADL | Fair plain | Δ |
|-------------------|-----|------------|---|
| Hit recall (≥1 relevant in top-k) | 1.00 | 0.80 | **+0.20** |
| Label recall (fraction of labels hit) | 0.97 | 0.73 | **+0.24** |

Scoring: TF-IDF on ADL index (L2 + L3 relations + resolved targets) vs fair plain (L2 only).
Phase B adds query-aligned relation overlap + neighbor propagation boost; zero-score ties do not count as hits.

Dataset: `data/aml/queries.json` v0.3 — 20 scenario queries + 5 **L3-only** opaque anchor queries (`q21`–`q25`) with `indexed-phrase` relations stripped from the plain baseline.

## Phase B+ RQ3 (optional hybrid embeddings)

```bash
pip install -e ".[dev,experiments-embeddings]"
python -m experiments.rq3_retrieval --mode phase_b --scorer hybrid -k 10
```

| Metric @10 (n=25) | ADL hybrid | Fair plain | Δ |
|-------------------|------------|------------|---|
| Hit recall | 1.00 | 0.80 | **+0.20** |
| Label recall | 0.98 | 0.73 | **+0.25** |

| Scenario subset (q01–q20, n=20) | Δ hit | Δ label |
|----------------------------------|-------|---------|
| Hybrid vs fair plain | **+0.00** | **+0.07** |

Scoring: `normalize(tfidf + l3_boost) + 0.5 * normalize(embedding)` over ADL index text (L2 + L3); plain baseline stays TF-IDF on L2-only fair plain. Model: `sentence-transformers/all-MiniLM-L6-v2` (lazy-loaded; CI runs without it via mock provider tests).

TF-IDF-only baseline (no embeddings): `--scorer tfidf` (default).

## RQ3 ablation (Table 1)

**Pointer:** Headline RQ3 Δ**+0.20** hit recall is **not** uniform across query types. Scenario-only **`q01`–`q20`** (`n=20`) show hit Δ**+0.00** under both TF-IDF and hybrid scorers; the full-set gap is driven by **`q21`–`q25`** L3-only opaque-anchor probes (ADL **1.00** vs plain **0.00**, Δ**+1.00**). See `docs/experiments/rq3_ablation.json` and `docs/paper/table2_results.md` before citing aggregate recall.

Source artifact: `docs/experiments/rq3_ablation.json` (generated by `python -m experiments.rq3_retrieval --mode phase_b -k 10 --scorer tfidf` and `--scorer hybrid`).

| Subset | Scorer | ADL recall | Plain | Delta |
|--------|--------|------------|-------|-------|
| Scenario (`q01`-`q20`, `n=20`) | TF-IDF | 1.00 | 1.00 | +0.00 |
| L3-only (`q21`-`q25`, `n=5`) | TF-IDF | 1.00 | 0.00 | +1.00 |
| Full (`n=25`) | TF-IDF | 1.00 | 0.80 | +0.20 |
| Scenario (`q01`-`q20`, `n=20`) | Hybrid | 1.00 | 1.00 | +0.00 |
| L3-only (`q21`-`q25`, `n=5`) | Hybrid | 1.00 | 0.00 | +1.00 |
| Full (`n=25`) | Hybrid | 1.00 | 0.80 | +0.20 |

## Ontology strict-mode pilot (Phase 2a–2c)

> **Status:** Milestones **2a** (`adl_core_ontology.yaml` + opt-in `--strict` predicate gate), **2b** (`OntologyManager`, `adl-lite ontology validate`), and **2c** (`adl_ontology_query` in `tools.py` + CLI) are implemented in-tree. **No RQ headline numbers** are claimed for ontology — pilot evidence is registry conformance only.

| Check | Result | Notes |
|-------|--------|-------|
| `adl-lite validate --strict examples/*.md` | **5/5 pass** | Curated corpus uses closed predicate set (10 predicates in registry) |
| `adl-lite validate --strict tests/fixtures/invalid_predicate.md` | **FAIL (expected)** | Unknown predicate `similar` rejected |
| Scripted sim (`ADL_STRICT_ONTOLOGY=1`) | Harness logs `strict_ontology: true` | Qualitative ablation: compare invalid-L3 rejection when strict on vs off (no aggregate stat yet) |

**Paper claim (honest):** ADL Lite positions an **operational ontology** middle layer — schema-guided extraction (**Method D**, Wang 2026) over Markdown authoring (**Method E**) — without OWL reasoners or triple stores. Strict validation is **opt-in** so LLM-authored drafts stay permissive by default. Pilot evidence is registry conformance on **n=5** curated examples plus a golden invalid fixture, not corpus-wide ablation statistics.

Reproduce:

```bash
adl-lite validate --strict examples/*.md
adl-lite validate --strict tests/fixtures/invalid_predicate.md  # expect exit 1
ADL_STRICT_ONTOLOGY=1 python -m experiments.run_sim --scripted
```

## Strict ontology ablation (Milestone 2c)

Scripted 5-agent sim with ontology registry enforcement (`ADL_STRICT_ONTOLOGY=1` or `ScriptedHarness(strict_ontology=True)`).

```bash
# Default (strict off) — repo examples pass SSA + optional predicate registry
python -m experiments.run_sim --scripted

# Strict — unknown L3 predicates fail reviewer validation before consensus
ADL_STRICT_ONTOLOGY=1 python -m experiments.run_sim --scripted
```

| Mode | Validate steps | Validation failures | Ontology errors | Notes |
|------|----------------|---------------------|-----------------|-------|
| Default (`strict_ontology=false`) | 3 | 0 | 0 | Repo `examples/*.md` use registered predicates |
| Strict (`ADL_STRICT_ONTOLOGY=1`) | 3 | 0 | 0 | Same corpus; no invalid L3 in scripted path |
| Strict + invalid fixture | 1 | 1 | 1 | `tests/fixtures/invalid_predicate.md` → `Unknown relation predicate: 'similar'` |

Agents can introspect the closed predicate/transition set before authoring L3 blocks:

```bash
adl-lite ontology query --json
adl-lite ontology query --from-status forked --to-status validated
python -c "from adl_lite.tools import adl_ontology_query; print(adl_ontology_query(from_status='forked', to_status='validated'))"
```

**Pilot read:** Strict mode is a **gate**, not a retrieval boost — on the current scripted corpus it adds zero false rejects because examples were authored against the registry. Negative ablation (LLM hallucinated predicates) is logged via `ontology_errors` in harness events when strict is on; measure on LLM discovery runs separately.

## Limitations (pilot)

- RQ pilots default to scripted transitions; LLM mode is optional and needs API credentials
- RQ3 retrieval defaults to TF-IDF; optional hybrid embeddings via `experiments-embeddings` extra
- Dataset concepts are generated minimal stubs
- Statistical significance not claimed; numbers are reproducible smoke metrics

## Next steps (post Phase 1)

- Human rubric labels for RQ1 on LLM-generated discoveries
- Enrich AML corpus per DATASET_GUIDE (expert relevance labels)
- Statistical tests when n ≥ 30 queries

