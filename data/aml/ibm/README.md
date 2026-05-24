# IBM AML (HI-Small) — local data guide

The [IBM AML dataset on Kaggle](https://www.kaggle.com/datasets/ealaxi/ibm-aml-transactions) provides
synthetic transaction graphs labeled with motifs such as fan-in, fan-out, scatter-gather, and cycle.

ADL Lite **does not** ship these files. Use them optionally to enrich evidence or future experiments;
the committed corpus maps motifs to ADL concepts under `data/aml/concepts/`.

## Prerequisites

- Kaggle account and API token (`~/.kaggle/kaggle.json`, mode `600`)
- [`kaggle`](https://github.com/Kaggle/kaggle-api) CLI: `pip install kaggle`

## Download (manual)

```bash
mkdir -p data/aml/ibm/raw
kaggle datasets download -d ealaxi/ibm-aml-transactions -p data/aml/ibm/raw
cd data/aml/ibm/raw && unzip -o '*.zip'
```

Expected artifacts (names may vary by Kaggle revision):

- `HI-Small_Trans.csv` — small labeled subset
- `HI-Medium_Trans.csv`, `HI-Large_Trans.csv` — optional scale-up

Keep large CSVs **gitignored** (add `data/aml/ibm/raw/` to local ignore if needed).

## Mapping to ADL concepts

| IBM motif (informal) | ADL concept id |
|----------------------|----------------|
| Fan-in | `aml-fan-in-pattern` |
| Fan-out | `aml-fan-out-pattern` |
| Gather-scatter | `aml-gather-scatter` |
| Scatter-gather | `aml-scatter-gather` |
| Bipartite | `aml-bipartite-pattern` |
| Cycle | `aml-cyclic-pattern` |
| Stack | `aml-stack-pattern` |
| Random | `aml-random-baseline` |

Do not report benchmark numbers from HI-Small until you have run analysis on your local copy.
