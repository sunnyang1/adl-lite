# Experiment outputs

Generated artifacts for Phase B / RQ1 pilots live here. Timestamped `llm_discovery_*.md` files are exploratory runs; the **active human-eval set** is the fifteen slug-named files referenced in `data/eval/human_rq1_template.json`.

## Backend proxy (no MIMO / OpenAI keys)

When external API keys are unavailable, materialize the fifteen strict-valid ADL discoveries (and three plain baselines) from in-repo templates:

```bash
export ADL_BACKEND_PROXY=1
python -m experiments.rq1_batch_discover --regenerate-all
```

Equivalent:

```bash
python -m experiments.backend_proxy
```

Flags:

| Flag / env | Effect |
|------------|--------|
| `ADL_BACKEND_PROXY=1` | Enable proxy mode for `rq1_batch_discover` |
| `--backend-proxy` | Same as setting the env var for one invocation |
| `--regenerate-all` | Rewrite all 15 `llm_discovery_*.md` RQ1 files + refresh `plain_discovery_*.md` |

Validate the active set:

```bash
adl-lite validate --strict experiments/outputs/llm_discovery_peripheral-trap.md \
  experiments/outputs/llm_discovery_smurfing-pattern.md \
  experiments/outputs/llm_discovery_crypto-mixer.md \
  experiments/outputs/llm_discovery_*_batch*.md
```

Plain baselines intentionally omit YAML and use vague pronouns for the unstructured comparison arm.
