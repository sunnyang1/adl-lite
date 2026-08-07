# ADL Lite — An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version: 0.6.0-alpha](https://img.shields.io/badge/version-v0.6.0--alpha-blue.svg)](https://github.com/sunnyang1/adl-lite/releases/tag/v0.6.0-alpha)
[![Tests: 1638](https://img.shields.io/badge/tests-1638-brightgreen.svg)]()
[![Coverage: 87%](https://img.shields.io/badge/coverage-87%25-brightgreen.svg)]()
[![Applied Ontology: under revision](https://img.shields.io/badge/Journal-Applied%20Ontology-orange.svg)](https://www.iospress.nl/journal/applied-ontology/)

> **"The world is the totality of facts, not of things." — Wittgenstein, Tractatus §1.1**

ADL Lite is a **Markdown-native, event-first capability registry** for LLM agent ecosystems. Every capability is an append-only, cryptographically hash-linked **EventChain** — status, confidence, and validators are **derived deterministically from event history**, never stored as mutable fields. Capabilities exist only as participants in events.

---

## Features

- **Event-first document model** — four layers (L1 YAML identity → L2 Markdown narrative → L3 typed relations → L4 actions), with status/confidence computed from the chain via CRDT least-upper-bound semantics that never regress.
- **Multi-agent consensus** — `register → validate → fork → deprecate` lifecycle with dynamic `N_min` (1 in dev, ≥2 in production for collusion resistance), SHA-256 hash-link integrity, and **N≥3 CRDT branch merge**.
- **Trust & provenance** — DID resolution (`did:key` / `did:web`), linked-data proofs, Merkle transparency anchors with batch verification, PROV-O / RDF-star / OWL 2 DL / JSON-LD exports, runtime SHACL (opt-in).
- **Pluggable persistence** — NetworkX (default), SQL, and **Neo4j** graph backends behind a common `GraphBackend` protocol; Hot/Warm/Cold memory with auto-archival.
- **Multiple interfaces** — CLI, FastAPI REST API (multi-tenant, JWT/API-key auth, rate limiting, metering, per-tenant quota), and an **MCP tool server**.
- **Verified** — 1638 tests, 87% coverage, TLA⁺ specs, Coq/Iris proof skeletons, and 30+ registered experiments (E1–E35).

---

## Installation

### Requirements

- **Python 3.10+** (CI tests 3.10–3.13)
- `pip` and a virtual environment (recommended)

### From source (recommended)

> The package is in alpha and is installed from the repository; a PyPI release will be published from tagged releases.

```bash
git clone https://github.com/sunnyang1/adl-lite.git
cd adl-lite

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Core install (everything you need to parse, validate, and run consensus)
pip install -e .

# Development install (adds pytest, ruff, mypy, rdflib, pyshacl, mcp, ...)
pip install -e ".[dev]"
```

Verify the install:

```bash
python -c "import adl_lite; print(adl_lite.__version__)"   # 0.6.0-alpha
adl-lite --help
```

### Optional extras

| Extra | Install command | Adds |
|-------|-----------------|------|
| `dev` | `pip install -e ".[dev]"` | pytest suite, ruff, mypy, rdflib, pyshacl, mcp, numpy, hypothesis |
| `embeddings` | `pip install -e ".[embeddings]"` | FAISS vector index + LLM embedding backends (semantic search) |
| `scale` | `pip install -e ".[scale]"` | FAISS, zstandard, msgpack (large-scale cold storage) |
| `gov` | `pip install -e ".[gov]"` | rdflib + pyshacl (SHACL / PROV-O governance) |
| `did` | `pip install -e ".[did]"` | web3, eth-account, coincurve (did:ethr resolution) |
| `neo4j` | `pip install -e ".[neo4j]"` | Neo4j graph backend (`adl-lite neo4j status\|check\|rebuild`) |
| `prod` | `pip install -e ".[prod]"` | PostgreSQL drivers (psycopg, asyncpg) for the FDE platform |
| `mcp` | `pip install -e ".[mcp]"` | FastMCP server (`adl-lite mcp`) |
| `experiments` | `pip install -e ".[experiments]"` | LLM clients + pygit2/prov for paper experiments |
| `v1` | `pip install -e ".[v1]"` | Redis + Celery (production task queue) |

Combine extras freely: `pip install -e ".[dev,embeddings,gov]"`.

### Docker (reproducibility environment)

```bash
docker build -t adl-lite-repro .
docker run --rm -v $(pwd)/docs/experiments:/app/docs/experiments adl-lite-repro
# default command runs all experiments; override with e.g. `E2 --verbose`
docker run --rm adl-lite-repro E2 --verbose
```

---

## Quick Start

Write a Markdown file describing a capability — the `adl:action` blocks *are* the event source of truth:

````markdown
---
adl_type: concept
adl_id: weather-data-retrieval
status: provisional
confidence: 0.0
scope: public
version: "1.0.0"
---

# Weather Data Retrieval

Fetches weather data from an external API.

```adl:action
action: register
actor: agent_1
reasoning: "Initial registration"
params:
  endpoint: "https://api.weather.example.com/v1/current"
```
````

Then validate and drive its lifecycle:

```bash
adl-lite validate examples/weather_data_retrieval.md    # semantic validation
adl-lite consensus register --adl-id cap-weather-api    # start a consensus chain
adl-lite consensus transition cap-weather-api --to validated --actor agent_2 --reason "tested OK"
adl-lite consensus verify cap-weather-api               # SHA-256 chain integrity
```

Or, the same in three lines of Python:

```python
from adl_lite.consensus import ConsensusEngine
from adl_lite.ontology import OntologyManager

engine = ConsensusEngine(ontology=OntologyManager(), dev_mode=True)
engine.register(concept_id="cap-weather-api", actor="agent_1")
engine.transition("cap-weather-api", to="validated", actor="agent_2", confidence=0.85)
print(engine.chains["cap-weather-api"].status)   # VALIDATED (derived, never stored)
```

---

## Usage

### CLI

```bash
adl-lite parse examples/weather_data_retrieval.md -o json   # parse → JSON dump
adl-lite validate examples/*.md                          # semantic validation
adl-lite validate --strict-template examples/*.md        # + L2 template conformance
adl-lite validate --strict examples/*.md                 # + reject unknown predicates
adl-lite store examples/weather_data_retrieval.md --db memory.db   # persist into ADLMemory
adl-lite related weather-data-retrieval --db memory.db   # graph-based related capabilities
adl-lite shacl examples/weather_data_retrieval.md        # runtime SHACL (needs [gov])
adl-lite ontology validate                               # core ontology registry checks
adl-lite ontology query --json                           # query predicates/actions/transitions
adl-lite consensus register examples/capital_reflux_trap.md    # or: --adl-id <id> without file
adl-lite consensus transition cap-weather-api --to validated --actor agent_2 --reason "OK"
adl-lite consensus verify cap-weather-api
adl-lite anchor --merkle --proofs-dir ./proofs           # Merkle transparency anchor
adl-lite verify-batch --anchor ANCHOR.md --proofs-dir ./proofs   # batch verification (v0.6.0)
adl-lite verify-inclusion cap-weather-api --proof ./proofs/cap-weather-api.proof.json
adl-lite normalize --input-dir ./concepts --threshold 0.92 --llm-provider mock  # dry-run
adl-lite normalize --input-dir ./concepts --threshold 0.92 --execute   # apply (needs [embeddings])
adl-lite neo4j status                                     # Neo4j backend health (needs [neo4j])
adl-lite mcp --transport stdio                            # MCP tool server (needs [mcp])
```

Run `adl-lite --help` (or `<subcommand> --help`) for the full reference.

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

# Production hardening: require ≥2 distinct validators
engine.set_production_mode()     # N_min ≥ 2; collusion-resistant
```

### Python — Key API Patterns

```python
from adl_lite import parse_file
from adl_lite.crdt import merge_event_chains
from adl_lite.key_registry import TransparencyAnchor
from adl_lite import ADLMemory

# Parse ADL files → EventChain
doc = parse_file("examples/weather_data_retrieval.md")
chain = doc.event_chain
print(chain.status, chain.confidence)  # Derived from chain, not stored

# Persist to hot/warm memory
mem = ADLMemory()
mem.store(doc)

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

# Vector semantic search (needs the [embeddings] extra)
from adl_lite import VectorIndex
index = VectorIndex()
index.add(doc.adl_id, doc.markdown_body)
hits = index.search("gradient explosion", top_k=5, threshold=0.8)

# OWL 2 DL import (round-trip with export)
from adl_lite import parse_owl_turtle, parse_owl_rdfxml
```

### REST API

Start the FastAPI server (core dependencies only — no extra required):

```bash
uvicorn adl_lite.api:app --reload --port 8000
```

Interactive docs at `http://localhost:8000/docs` (Swagger UI).

```bash
curl -X POST http://localhost:8000/api/v1/consensus/register \
  -H "Content-Type: application/json" \
  -d '{"adl_id": "cap-weather-api", "actor": "agent_1", "domain": "weather", "scope": "public"}'
curl -X POST http://localhost:8000/api/v1/consensus/transition \
  -d '{"adl_id": "cap-weather-api", "to": "validated", "actor": "agent_2", "confidence": 0.85}'
curl http://localhost:8000/api/v1/consensus/status/cap-weather-api
curl -X POST http://localhost:8000/api/v1/consensus/mode/production   # N_min ≥ 2

# Multi-agent control plane (M1a-M4) + single-source-of-truth meta (closure):
curl http://localhost:8000/api/v1/agents                              # agent identities
curl http://localhost:8000/api/v1/tasks                               # task lifecycle
curl http://localhost:8000/api/v1/runtime/status                      # backlog (P1-6)
curl http://localhost:8000/api/v1/meta/task-transitions               # state machine
curl http://localhost:8000/api/v1/meta/roles                          # role whitelists
```

Production hardening is opt-in via `create_app()`: JWT/API-key auth,
rate limiting, per-tenant metering, and quota enforcement
(`create_app(auth_enabled=True, api_keys={...}, quota_max_api_calls=...,
quota_period="daily")`) — exceeding a quota returns **HTTP 429** with a
`Retry-After` header.

**Admin login** (trust-root bootstrap): set `ADMIN_USERNAME`/`ADMIN_PASSWORD`
env vars; the OAuth2 token endpoint then issues `role="admin"` JWTs for those
credentials, which unlock the admin-gated agent endpoints
(`/api/v1/agents/register`, `/api/v1/agents/{did}/admin-validate`,
`/api/v1/admin/public-key`, `/api/v1/admin/trust/diversity`).

### Dashboard Platform

A management UI for the multi-agent system lives in `dashboard/`
(Vite + React 18 + MUI v5 + Tailwind + TanStack Query):

```bash
cd dashboard && npm install && npm run dev    # http://localhost:5173
# backend on :8000 (vite proxies /api/v1 automatically)
```

Pages: **Overview** (health/mode), **Capabilities** (discovery chains),
**Agents** (identity + reputation, admin validate / public-key registration),
**Tasks** (lifecycle actions driven by the backend state machine),
**Runtime** (backlog visibility), **Trust** (B4 diversity switch). Sign in
with an admin credential to unlock admin actions.

### MCP Tool Server

Expose the registry to MCP-capable agents (requires the `[mcp]` extra):

```bash
pip install -e ".[mcp]"
adl-lite mcp --transport stdio          # or --transport streamable-http --port 8000
```

The server publishes **10 tools** (register / transition / status / history /
fork / validate / anchor / verify-batch / ontology query / normalize), 2
resources, and 1 prompt. Programmatic access:
`from adl_lite.mcp_server import create_mcp_server; server = create_mcp_server()`.

---

## Architecture

```
Markdown file (L1/L2/L3/L4) → ADLParser → EventChain → ConsensusEngine → ADLMemory
                                                                ↓
                      OntologyManager → ActionExecutor → REST API / CLI / MCP
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
| **γ\* (C)** | 6 confidence strategies: γ_agg, γ_cal, γ_ewma, γ_ctx, γ_band + MARGIN calibrator |
| **dev_mode** | N_min=1 (single validator) vs production N_min≥2 (collusion resistance) |
| **GraphBackend** | Pluggable graph persistence: NetworkX (default), SQL, Neo4j |

---

## Roadmap

| Status | Item |
|--------|------|
| ✅ v0.6.0-alpha | Complete version: multi-tenant API + quota, N≥3 CRDT merge, Merkle batch verify, MCP server, E34/E35 |
| ✅ v0.5.0-alpha | Formal methods (TLA⁺/Coq), scale arch (split-lock, zstd), REST API |
| ✅ v0.4.0-alpha | DID (did:web/ethr), SHACL, expert calibration, vector + LLM |
| ✅ v0.3.5 | CRDT migration (LUB status + G-Counter confidence) |
| 🔄 Active | Applied Ontology journal — under major revision (39pp, 9 theorems) |

---

## Experiments

30 registered experiments (E1–E35). Run them:

```bash
python -m experiments.runner list
python -m experiments.runner E2 --verbose   # single experiment
python -m experiments.runner all            # all experiments (~5–15 min)
./reproduce.sh quick                        # E1–E4 + E24 (~30s)
./reproduce.sh test                         # pytest suite only
```

Key results: E21 100k events < 1GB memory, E24 10k synthetic chains T1–T7 validated, E30 LLM canonicalization of near-duplicates.

---

## Project Structure

```
adl-lite/
├── adl_lite/            # Core package (55+ modules)
├── experiments/         # 30 registered experiments (E1–E35)
├── tests/               # 1638 tests, 87% coverage
├── docs/                # Paper submission, runbooks, ontology artifacts
├── specs/               # TLA+ formal specifications
├── formal/coq/          # Coq/Iris proof skeleton
├── examples/            # ADL Markdown samples + CRDT demo script
├── CONTRIBUTING.md      # Contribution guide
└── reproduce.sh         # One-command reproduction script
```

---

## Contributing

Contributions are welcome — code, docs, experiments, formal proofs, ontology
predicates. In short:

1. **Fork** the repo and create a topic branch (`feat/...`, `fix/...`, `docs/...`).
2. `pip install -e ".[dev]"` and `pre-commit install` (ruff + mypy run on every commit).
3. Make your change, add tests, and run `ruff check adl_lite/ tests/`,
   `mypy adl_lite/ --ignore-missing-imports`, and
   `pytest tests/ -m "not slow"` locally.
4. Open a PR against `main` and add a `CHANGELOG.md` entry.

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide (setup, style,
testing, experiments, CI/CD).

---

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 CEIEC AI Infrastructure.
