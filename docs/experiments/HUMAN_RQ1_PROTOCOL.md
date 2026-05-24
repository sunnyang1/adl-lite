# Human RQ1 Referent Clarity Study — Protocol

> **Status: CANCELLED (2026-05-24).** The paper uses **LLM-as-judge / proxy judges only** for RQ1 subjective clarity. This protocol and `human_rq1_template.json` are retained for audit and optional future work — do not report human means in the manuscript.

Step-by-step instructions for running the human inter-rater study that supplements LLM-as-judge RQ1 pilots. **Do not copy LLM proxy scores into human fields.**

## Purpose

Validate whether ADL L2 prose is clearer than (a) fair-plain stripped L2 and (b) unstructured plain-LLM notes, using the same 1–5 referent clarity rubric as `prompts/judge_referent_clarity.md`.

## Comparison arms

| Arm | What raters read | Template field |
|-----|------------------|----------------|
| **ADL L2** | Markdown body only (ignore L1 YAML, L3 blocks) | `referent_clarity` |
| **Fair plain** | Same discovery, L2 wording with ADL structure stripped | `referent_clarity_fair_plain` |
| **Plain LLM** | Unstructured MiMo note (`plain_discovery_*.md`, one per AML topic) | `referent_clarity_plain_llm` |

## Materials

1. **Rating template:** `data/eval/human_rq1_template.json` (15 active discoveries + 5 reserve slots)
2. **Rubric:** `prompts/judge_referent_clarity.md`
3. **ADL discoveries:** `experiments/outputs/llm_discovery_*.md` (paths in template)
4. **Fair-plain extracts:** generate on demand with `adl_to_fair_plain(path)` or read stripped L2 from the same file after mentally ignoring L1/L3
5. **Plain-LLM baselines:** `experiments/outputs/plain_discovery_{peripheral-trap,smurfing-pattern,crypto-mixer}.md`
6. **LLM reference (do not copy):** `docs/experiments/rq1_llm_judge_summary.json`

## Rater instructions

1. Read the rubric once before scoring.
2. Score **L2 prose only** — never YAML front matter or ` ```adl:* ` blocks for the ADL arm.
3. Use integers **1–5** (higher = clearer entity/referent anchors).
4. For dual-rater rows, assign independent scores; do not discuss until both submit.
5. Flag adjudication when `|referent_clarity - referent_clarity_b| >= 2` (see template `disagreement_threshold`).

## Recording scores

Edit `data/eval/human_rq1_template.json` (or a copy, e.g. `data/eval/human_rq1_completed.json`):

```json
{
  "adl_id": "disc-llm-peripheral-trap",
  "referent_clarity": 4,
  "referent_clarity_b": 5,
  "referent_clarity_fair_plain": 4,
  "referent_clarity_plain_llm": 2,
  "rater": "R01",
  "rater_b": "R02",
  "rating_completed_at": "2026-05-24T12:00:00Z"
}
```

Leave fields `null` until scored. Reserve slots (rows with `"adl_id": null`) are for future discoveries.

## Recommended design

- **Raters:** 5–10 independent readers (AML analysts, compliance engineers, or CS grad students with rubric training)
- **Items:** 15 active discoveries (3 AML topics × batch expansion)
- **Dual rating:** At least 20% of items double-scored for inter-rater reliability
- **Blinding:** Randomize arm order; do not label files as "ADL" vs "plain" in the UI shown to raters

## Analysis (after ratings exist)

```bash
# Default: reads template, writes summary
python -m experiments.rq1_human_eval

# Custom completed file
python -m experiments.rq1_human_eval \
  --template data/eval/human_rq1_completed.json \
  --out docs/experiments/rq1_human_summary.json
```

Output: `docs/experiments/rq1_human_summary.json` with:

- Per-arm means (`adl_l2`, `fair_plain_l2`, `plain_llm_unstructured`)
- Deltas (`adl_minus_fair_plain`, `adl_minus_plain_llm`)
- Inter-rater placeholder (`inter_rater.icc` stays `null` until exported to external ICC tooling)

Paste human headline numbers into `docs/experiments/RESULTS.md` under the RQ1 human section when `n_rated_adl >= 5`.

## Current status

| Item | Status |
|------|--------|
| Template + 15 discoveries | Ready |
| LLM proxy scores (reference) | Complete (`rq1_llm_judge_summary.json`) |
| Human `referent_clarity` fields | **Pending** (all `null`) |
| Analysis script | Ready (`experiments/rq1_human_eval.py`) |

## Reproduce LLM baseline (reference only)

```bash
python -m experiments.rq1_llm_judge --summarize-from-template --proxy-only --no-plain-fixture
```
