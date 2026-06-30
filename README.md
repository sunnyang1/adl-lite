# ADL Lite — An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version: 0.6.0-alpha](https://img.shields.io/badge/version-v0.6.0--alpha-blue.svg)](https://github.com/sunnyang1/adl-lite/releases/tag/v0.6.0-alpha)
[![Tests: 1358 PASS](https://img.shields.io/badge/tests-1358%20PASS-brightgreen.svg)]()
[![Coverage: 87%](https://img.shields.io/badge/coverage-87%25-brightgreen.svg)]()
[![Applied Ontology: under revision](https://img.shields.io/badge/Journal-Applied%20Ontology-orange.svg)](https://www.iospress.nl/journal/applied-ontology/)

> **"The world is the totality of facts, not of things." — Wittgenstein**

ADL Lite is a **Markdown-native, event-first capability registry** for LLM agent ecosystems. Every capability is an append-only, cryptographically hash-linked EventChain — status, confidence, and validators are **derived deterministically from event history**, never stored as mutable fields.

---

## Quick Start

```bash
git clone https://github.com/sunnyang1/adl-lite.git && cd adl-lite
pip install -e ".[dev]"        # dev install with pytest + ruff + mypy
pytest tests/ -m "not slow" -v # 1358 tests, 87% coverage
uvicorn adl_lite.api:app --reload --port 8000  # REST API server
```

Install extras as needed: `pip install -e ".[embeddings]"` for vector search, `pip install -e ".[did]"` for did:ethr, `pip install -e ".[gov]"` for SHACL.

---

## Usage

### CLI

```bash
adl-lite validate examples/*.md                          # Validate ADL files
adl-lite consensus register examples/capital_reflux_trap.md  # Lifecycle management
adl-lite anchor --merkle --proofs-dir ./proofs           # Merkle transparency anchor
adl-lite verify-batch --anchor ANCHOR.md --proofs-dir ./proofs  # Batch verification (v0.6.0)
adl-lite normalize --input-dir ./concepts --threshold 0.92  # LLM normalization
adl-lite ontology query --json                           # Ontology queries
```

### Python — End-to-End Walkthrough

```python
from adl_lite.consensus import ConsensusEngine
from adl_lite.ontology import OntologyManager

# Set up the consensus engine
mgr = OntologyManager()
engine = ConsensusEngine(ontology=mgr, dev_mode=True)
engine.register(concept_id="cap-weather-api", actor="agent_1")
chain = engine.chains["cap-weather-api"]
assert chain.status.name == "PROVISIONAL"

# A second agent validates with a confidence score
engine.transition("cap-weather-api", to="validated", actor="agent_2", confidence=0.85)
print(chain.status, chain.confidence)  # VALIDATED 0.85 (G-Counter max, never decreases)

# Fork and deprecate
engine.fork("cap-weather-api", child_id="cap-weather-api-v2", actor="agent_3")
engine.transition("cap-weather-api", to="deprecated", actor="agent_2")
assert chain.verify_integrity()  # SHA-256 cryptographic hash-link verification
```

### Python — Key API Patterns

```python
from adl_lite import parse_file
from adl_lite.crdt import merge_event_chains
from adl_lite.key_registry import TransparencyAnchor

# Parse ADL files → EventChain
doc = parse_file("examples/weather_data_retrieval.md")
chain = doc.event_chain
print(chain.status, chain.confidence)  # Derived from chain, not stored

# N≥3 CRDT chain merge (v0.6.0)
chain_d = merge_event_chains(chain_a, chain_b, chain_c, chain_d)

# Merkle batch verification (v0.6.0)
anchor = TransparencyAnchor("ANCHOR.md")
root = anchor.anchor([chain_a, chain_b], use_merkle=True, proofs_dir="./proofs")
results = TransparencyAnchor.verify_batch([chain_a, chain_b], root, proofs)

# DID verification
from adl_lite import resolve_did, verify_did_signature
doc = resolve_did("did:web:example.com:path")
assert verify_did_signature("did:key:z...", b"message", signature)

# Semantic Web exports
from adl_lite import export_owl, export_jsonld, document_to_rdfstar_turtle
owl = export_owl(doc, format="turtle")

# Vector semantic search
from adl_lite import VectorIndex
index = VectorIndex()
index.add(doc.adl_id, doc.markdown_body)
hits = index.search("gradient explosion", top_k=5, threshold=0.8)
```

### REST API

```bash
uvicorn adl_lite.api:app --reload --port 8000

curl -X POST http://localhost:8000/api/v1/consensus/register \
  -H "Content-Type: application/json" \
  -d '{"adl_id": "cap-weather-api", "actor": "agent_1", "domain": "weather", "scope": "public"}'
curl -X POST http://localhost:8000/api/v1/consensus/transition \
  -d '{"adl_id": "cap-weather-api", "to": "validated", "actor": "agent_2", "confidence": 0.85}'
curl http://localhost:8000/api/v1/consensus/status/cap-weather-api
curl -X POST http://localhost:8000/api/v1/consensus/mode/production  # N_min ≥ 2
```

Interactive docs at `http://localhost:8000/docs` (Swagger UI).

---

## Architecture

```
Markdown file (L1/L2/L3/L4) → ADLParser → EventChain → ConsensusEngine → ADLMemory
                                                                 ↓
                      OntologyManager → ActionExecutor → REST API / CLI
```

**Four-layer document model**: L1 = identity (YAML), L2 = narrative (Markdown), L3 = relations (typed semantics), L4 = actions (event source of truth). Status derived from chain via CRDT LUB semantics — never regresses.

| provisional | validated | deprecated | forked | archived |
|:---:|:---:|:---:|:---:|:---:|

---

## Key Concepts

| Term | Definition |
|------|-----------|
| **EventChain** | Append-only, hash-linked event sequence. Capability = chain. |
| **δ(C) / γ(C)** | Deterministic status / G-Counter max confidence from event history |
| **CRDT merge** | LWW-Set merge via pairwise fold — N≥3 branches (Theorem 9, v0.6.0) |
| **γ_\* (C)** | 6 strategies: γ_agg, γ_cal, γ_ewma, γ_ctx, γ_band + MARGIN calibrator |
| **dev_mode** | N_min=1 (single validator) vs production N_min≥2 (collusion resistance) |

---

## Roadmap

| Status | Item |
|--------|------|
| ✅ v0.6.0-alpha | Complete version: N≥3 CRDT merge, Merkle batch verify, DID full |
| ✅ v0.5.0-alpha | Formal methods (TLA⁺/Coq), scale arch (split-lock, zstd), REST API |
| ✅ v0.4.0-alpha | DID (did:web/ethr), SHACL, expert calibration, vector + LLM |
| ✅ v0.3.5 | CRDT migration (LUB status + G-Counter confidence) |
| 🔄 Active | Applied Ontology journal — under major revision (39pp, 9 theorems) |

---

## Experiments

28 registered experiments (E1–E30). Run them:

```bash
python -m experiments.runner list
python -m experiments.runner E2 --verbose   # single experiment
python -m experiments.runner all            # all experiments (~5–15 min)
./reproduce.sh quick                        # E1–E4 + E24 (~30s)
```

Key results: E21 100k events < 1GB memory, E24 10k synthetic chains T1–T7 validated, E30 LLM canonicalization of near-duplicates.

---

## Project Structure

```
adl-lite/
├── adl_lite/            # Core package (20+ modules)
├── experiments/         # 28 registered experiments (E1–E30)
├── tests/               # 1358 tests, 87% coverage
├── docs/                # Paper submission, runbooks, ontology artifacts
├── specs/               # TLA+ formal specifications
├── formal/coq/          # Coq/Iris proof skeleton
└── reproduce.sh         # One-command reproduction script
```

---

## Contributing

Fork → branch → PR. Pre-commit runs ruff + mypy on every commit. See [CONTRIBUTING.md](CONTRIBUTING.md) for details (or `pre-commit install` to set up hooks).

---

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 CEIEC AI Infrastructure.
