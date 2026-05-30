# ADL Lite — Evaluation Results (Pilot)

> **Venue framing (ESWC / ISWC 2027):** Lead evidence = **operational ontology** strict validation (**5/5** examples) + **RQ3** L3-only retrieval (**Δ +1.00** on `q21`–`q25`) + **RQ4** scope (**99/99** denied; 33 indexed concepts × 3 requesters). Supporting = **RQ2** lifecycle traceability (scripted **8** vs plain **0**); secondary = **RQ1** LLM-judge (**fair-plain Δ = 0**; unstructured plain-LLM **+1.4/+1.6**). **Human RQ1 cancelled** (agent/LLM-judge only; 2026-05-24).

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
    label_recall_delta: 0.22
    scenario_hit_delta: 0.00            # q01-q20
    l3_only_hit_delta: 1.00           # q21-q25
  rq4_scope:
    leaks: 0
    probes_denied: 99
    probes_total: 99
  ontology_strict:
    examples_pass: 5
    invalid_fixture_fails: true
  human_rq1:
    status: cancelled
    n_rated: 0
    note: agent_llm_judge_only
artifacts:
  - docs/experiments/summary_phase_b.json
  - docs/experiments/rq1_llm_judge_summary.json
  - docs/experiments/rq3_ablation.json
  - docs/experiments/rq1_human_summary.json
  - docs/paper/table2_results.md
reproduce: docs/experiments/RESEARCH_LOOP_CHECKLIST.md
```

> [!summary] Paper-ready summary (evidence-ordered)
> - **Ontology (strict):** `adl-lite validate --strict examples/*.md` → **5/5 pass**; invalid fixture fails on unknown predicate `similar`.
> - **RQ3 (L3-sensitive retrieval):** Full-set hit recall **1.00** vs **0.80** (**Δ +0.20**, `n=25`); scenario `q01`–`q20` hit **Δ +0.00**; L3-only `q21`–`q25` hit **Δ +1.00** (`rq3_ablation.json`).
> - **RQ4 (scope):** **0** leaks; **99/99** cross-scope probes denied (`n_concepts=33` × 3 requesters).
> - **RQ2 (lifecycle):** Scripted **8** transitions vs plain **0**; MiMo batch mean **2.0**/run (**not** comparable to scripted **8** total).
> - **RQ1 (secondary):** Fair-plain LLM-judge **Δ = 0** (`n=15`); vs unstructured plain-LLM **+1.40 / +1.60** (~**+1.50** pooled). **Human RQ1 cancelled** (agent/LLM-judge only; 2026-05-24).
> - **Reproduce:** `pytest tests/ -v && python -m experiments.run_phase_b && ./scripts/demo_pipeline.sh --scripted && python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture`

## Phase B summary (v0.3.0)

| Track | Metric | ADL / Phase B | Baseline | Δ / status |
|-------|--------|---------------|----------|------------|
| **Ontology** | Strict validation (`examples/*.md`) | **5/5 pass** | — | Registry conformance |
| **Ontology** | Golden negative (`invalid_predicate.md`) | **FAIL (expected)** | — | Unknown predicate rejected |
| **RQ3** | Hit recall @10 (TF-IDF, `n=25`) | **1.00** | 0.80 fair plain | **+0.20** (see L3 ablation) |
| **RQ3** | Hit recall — scenario `q01`–`q20` | 1.00 | 1.00 | **+0.00** |
| **RQ3** | Hit recall — L3-only `q21`–`q25` | 1.00 | 0.00 | **+1.00** |
| **RQ3** | Label recall @10 (TF-IDF) | **0.90** | 0.68 | **+0.22** |
| **RQ4** | Scope leaks / probes | **0** leaks | not instrumented | **99/99** denied |
| **RQ2** | Scripted consensus transitions | **8** (3 validated) | 0 (plain) | Lifecycle trace |
| **RQ2** | MiMo batch (`n=10`) | mean **2.0** transitions | scripted **8** total | **−6.0** (caveat: not like-for-like) |
| **RQ1** | Heuristic ambiguity rubric (`n_pairs=25`) | mean **0.0** | mean **0.0** | **0%** reduction |
| **RQ1** | LLM-as-judge (`n=15`) | see `rq1_llm_judge_summary.json` | fair-plain **Δ=0**; plain-LLM **+1.40/+1.60** | **Human cancelled** (LLM-judge only) |

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
| Ontology strict (`examples/`) | **5/5 pass** | — | Closed predicate registry |
| RQ3 hit recall @10 (full, `n=25`) | **1.00** | **0.80** fair plain | **Δ +0.20**; scenario subset **Δ 0** |
| RQ4 scope leaks | **0** | uncontrolled reads | **99/99** probes denied |
| RQ2 consensus transitions (scripted) | **8** | **0** | Append-only chain |
| RQ1 LLM-judge vs fair-plain (`n=15`) | — | paired L2 | **Δ = 0** |
| RQ1 LLM-judge vs unstructured plain-LLM | — | slug prose | **+1.4 / +1.6** per judge |

Run `python -m experiments.run_all` for exact pilot numbers on your machine.

## Research questions (evidence order)

### Ontology — strict validation (Phase 2a–2b)

See [Ontology strict-mode pilot](#ontology-strict-mode-pilot-phase-2a2c) below. **5/5** examples pass `--strict`; invalid fixture fails. No RQ headline lift claimed.

### RQ3 — L3-sensitive retrieval

15 AML queries in legacy scripts; Phase B uses **25** queries (`data/aml/queries.json` v0.3: **20** scenario + **5** L3-only).

- Script: `experiments/rq3_retrieval.py`
- ADL index uses L3 relation count as tie-break boost; plain baseline strips L3

### RQ4 — Scope leakage

Probe cross-scope reads with `ADLValidator.validate_scope_access`.

- Script: `experiments/rq4_leakage.py`
- Target: **0 leaks** for ADL (deny by default on private scope)

### RQ2 — Consensus lifecycle traceability

ADL records explicit transitions; plain Markdown has no lifecycle chain.

- Script: `experiments/rq2_consensus.py`
- Metric: count of `ConsensusEntry` append operations to reach `validated`
- **Scripted baseline:** 8 transitions (3 docs validated, 5 docs total)
- **LLM batch (MiMo `mimo-v2.5-pro`, n=10):** mean **2.0** transitions/run — **not** comparable to scripted **8** without workload redesign; see `docs/experiments/rq2_llm_summary.json`

### RQ1 — Referent clarity (secondary)

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
| Human ratings | **Cancelled** (2026-05-24); RQ1 subjective arm = LLM-as-judge / proxy only. Template retained for audit (`human_rq1_template.json`). |

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
| Label recall (fraction of labels hit) | 0.90 | 0.68 | **+0.22** |

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
| Label recall | 0.9333 | 0.68 | **+0.2533** |

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

- Human RQ1 **cancelled** (2026-05-24); optional second judge provider or spot-checks only if revisiting subjective claims
- Enrich AML corpus per DATASET_GUIDE (expert relevance labels)
- Statistical tests when n ≥ 30 queries

