# AML domain corpus (ADL Lite — Capability Registry)

This folder is the **financial AML evaluation domain** for ADL Lite capability registry. The corpus supports
**capability discovery and multi-agent consensus**, not production transaction detection.

## Two-layer strategy

| Layer | Role | Location |
|-------|------|----------|
| **FATF typology skeleton** | Regulatory and operational AML capabilities (placement, layering, integration, trade, VA, PEP, etc.) | `concepts/aml-*.md` (non-IBM ids) |
| **IBM HI-Small graph motifs** | Eight published graph patterns used as **capability anchors** linked to typologies via `specialisation-of` / `isomorphic-to` | `concepts/aml-*-pattern*.md`, `concepts/aml-*-scatter*.md`, `concepts/aml-random-baseline.md` |

Raw HI-Small transaction CSVs are optional grounding data; they are **not** the primary ADL
artifact. See `ibm/README.md` for download instructions.

## Layout

```
data/aml/
├── README.md           # this file
├── manifest.json       # capability index (version 0.2)
├── queries.json        # 25 queries (q01–q20 scenario NL; q21–q25 L3-only tokens)
├── loader.py           # ensure_dataset, index_all
├── concepts/           # ADL capability documents
├── ibm/                # HI-Small download notes (no large files in repo)
└── scripts/
    ├── validate_corpus.py
    └── run_domain_smoke.py
```

## Validation

```bash
adl-lite validate --strict data/aml/concepts/*.md
python data/aml/scripts/validate_corpus.py
python data/aml/scripts/run_domain_smoke.py
```

## Query labeling

- **q01–q20**: natural-language monitoring scenarios (L2-dependent retrieval).
- **q21–q25**: opaque L3 `indexed-phrase` tokens (relation-target dependent).

Expert multi-label `relevant` lists live in `queries.json`; do not infer labels from filenames alone.

## Scope honesty

Statistics from IBM HI-Small (class balance, AUC, etc.) require a local Kaggle download.
This repository documents patterns and ADL capabilities only until you attach the CSV locally.

**Note:** The E6 evaluation uses HI-Small as an **architectural stress test** (9,000 REGISTER events from transaction import, 3.2% synthetic governance events). It validates the EventChain data structure at scale, not domain-level AML detection effectiveness.
