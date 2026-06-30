# ADL Lite — An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version: 0.6.0-alpha](https://img.shields.io/badge/version-v0.6.0--alpha-blue.svg)](https://github.com/sunnyang1/adl-lite/releases/tag/v0.6.0-alpha)
[![ESWC/ISWC 2027 Backup](https://img.shields.io/badge/Backup-ESWC%2FISWC%202027-blue.svg)](https://2027.eswc-conferences.org/)
[![Applied Ontology: under revision](https://img.shields.io/badge/Journal-Applied%20Ontology-orange.svg)](https://www.iospress.nl/journal/applied-ontology/)
[![Tests: 1358 PASS](https://img.shields.io/badge/tests-1358%20PASS-brightgreen.svg)]()
[![Coverage: 87%](https://img.shields.io/badge/coverage-87%25-brightgreen.svg)]()
[![Release Readiness: GO](https://img.shields.io/badge/release%20readiness-GO-brightgreen.svg)]()
[![API: FastAPI](https://img.shields.io/badge/API-FastAPI%20REST-009688.svg)]()
[![Paper: 39pp](https://img.shields.io/badge/paper-39pp-blue.svg)]()

> **"The world is the totality of facts, not of things." — Wittgenstein, Tractatus Logico-Philosophicus §1.1**

ADL Lite is an **event-first, Markdown-native capability-lifecycle registry** for LLM agent ecosystems. Each capability (tool, API, knowledge domain) is represented as an **append-only, cryptographically hash-linked EventChain**. Status, confidence, and validators are **never stored as mutable fields** — all derived deterministically from the event history.

ADL Lite fills the gap between **KYA** (permissions layer) and **AgentSafe** (architecture-level governance): a lightweight, verifiable registry that records what agents can do, how capabilities evolve, and whether they remain trustworthy.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
  - [CLI](#cli)
  - [Python API](#python-api)
  - [REST API](#rest-api)
- [Architecture](#architecture)
- [Core Concepts](#core-concepts)
- [Experiments](#experiments)
- [Project Structure](#project-structure)
- [Paper Status](#paper-status)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

### Prerequisites

- **Python 3.10+** (tested on 3.10, 3.11, 3.12)
- **pip** (bundled with Python)
- **Git** (for cloning and pre-commit hooks)
- **[Docker](https://www.docker.com/)** (optional, for reproducible experiment runs)

### Option 1: Development Install (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/sunnyang1/adl-lite.git
cd adl-lite

# 2. (Recommended) Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (PowerShell)

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 4. (Optional) Install pre-commit hooks for automatic linting
pip install pre-commit
pre-commit install
```

### Option 2: Install from PyPI

```bash
pip install adl-lite
```

### Option 3: Docker

```bash
docker build -t adl-lite .
docker run --rm adl-lite pytest tests/ -v
```

### Optional Extras

ADL Lite uses optional dependency groups so the core package stays lightweight.
Install only what you need:

| Extra | Install Command | What It Enables |
|-------|----------------|-----------------|
| `dev` | `pip install -e ".[dev]"` | pytest, ruff, mypy, rdflib, pyshacl |
| `experiments` | `pip install -e ".[experiments]"` | openai, anthropic (LLM experiment scripts) |
| `experiments-embeddings` | `pip install -e ".[experiments-embeddings]"` | sentence-transformers for near-duplicate detection |
| `embeddings` | `pip install -e ".[embeddings]"` | FAISS vector index + sentence-transformers + OpenAI |
| `scale` | `pip install -e ".[scale]"` | FAISS, zstd, msgpack (large-scale cold storage) |
| `did` | `pip install -e ".[did]"` | web3, eth-account, coincurve (did:ethr resolution) |
| `gov` | `pip install -e ".[gov]"` | rdflib, pyshacl (SHACL validation) |
| `prod` | `pip install -e ".[prod]"` | PostgreSQL drivers (psycopg, asyncpg) |
| `v1` | `pip install -e ".[v1]"` | redis, celery (distributed task queue) |

You can combine multiple extras:

```bash
pip install -e ".[dev,embeddings,scale,gov]"
```

### Verify the Installation

```bash
# Check the CLI is on your PATH
adl-lite --help

# Run the test suite (fast tests only)
pytest tests/ -m "not slow" -v

# Run a quick experiment
python -m experiments.runner E1
```

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/sunnyang1/adl-lite.git
cd adl-lite
pip install -e ".[dev]"

# Run all experiments
python -m experiments.runner all

# List experiments
python -m experiments.runner list

# Run single experiment
python -m experiments.runner E2

# Run tests (1358 passed, 87% coverage)
pytest tests/ -v --cov=adl_lite --cov-report=term-missing

# Run fast tests only (excludes slow benchmarks)
pytest tests/ -m "not slow" -v --cov=adl_lite

# Start the REST API server
uvicorn adl_lite.api:app --reload --port 8000
```

---

## Usage Examples

### End-to-End Walkthrough

This walkthrough shows a complete capability lifecycle: **register → validate → fork → deprecate**.

```python
from adl_lite import Event, EventChain, EventType, DiscoveryStatus
from adl_lite.consensus import ConsensusEngine
from adl_lite.ontology import OntologyManager

# 1. Set up the consensus engine
#    dev_mode=True  → N_min=1 (single validator, good for development)
#    dev_mode=False → N_min≥2 (collusion resistance, use in production)
mgr = OntologyManager()
engine = ConsensusEngine(ontology=mgr, dev_mode=True)

# 2. An agent registers a new capability
engine.register(concept_id="cap-weather-api", actor="agent_1")
chain = engine.chains["cap-weather-api"]

print(chain.status)       # DiscoveryStatus.PROVISIONAL
print(chain.confidence)   # 0.0 (no validations yet)

# 3. A second agent validates it with a confidence score
engine.transition(
    concept_id="cap-weather-api",
    to="validated",
    actor="agent_2",
    confidence=0.85,
)

print(chain.status)       # DiscoveryStatus.VALIDATED
print(chain.confidence)   # 0.85 (G-Counter max — never decreases)

# 4. A third agent disagrees and forks a new version
engine.fork(
    concept_id="cap-weather-api",
    child_id="cap-weather-api-v2",
    actor="agent_3",
)

print(chain.status)       # DiscoveryStatus.FORKED (parent retains validated)

# 5. The original is deprecated after the fork is validated
engine.transition(
    concept_id="cap-weather-api",
    to="deprecated",
    actor="agent_2",
)

print(chain.status)       # DiscoveryStatus.DEPRECATED

# 6. Verify cryptographic integrity of the entire chain
assert chain.verify_integrity()  # SHA-256 hash-link verification

# Full audit log
for event in chain.history():
    print(f"  {event['event_type']:12s}  actor={event['actor']}  "
          f"hash={event['hash'][:16]}...")
```

<details>
<summary><b>Parsing an ADL Markdown file</b></summary>

```python
from adl_lite import parse_file

# Parse a capability Markdown file (L1 front matter + L2 body + L3/L4 blocks)
doc = parse_file("examples/weather_data_retrieval.md")

# L1 — derived front-matter snapshot
print(doc.front_matter.adl_id)     # "weather-data-retrieval"
print(doc.front_matter.status)     # DiscoveryStatus.DEPRECATED
print(doc.front_matter.confidence) # 0.85

# L2 — Markdown body (human/LLM narrative)
print(doc.markdown_body[:200])

# L3 — semantic relation blocks
for rel in doc.relations:
    print(f"  {rel.source} --{rel.relation}--> {rel.target}")

# L4 — typed action blocks (the event source of truth)
for action in doc.actions:
    print(f"  {action.action:10s}  actor={action.actor}")

# The EventChain is derived from L4 action blocks
chain = doc.event_chain
print(chain.status)               # Derived from chain, not stored
print(chain.confidence)           # G-Counter max over VALIDATE events
```

</details>

<details>
<summary><b>Multi-agent consensus with collusion resistance</b></summary>

```python
from adl_lite.consensus import ConsensusEngine
from adl_lite.ontology import OntologyManager

mgr = OntologyManager()
engine = ConsensusEngine(ontology=mgr, dev_mode=True)

# Register a concept
engine.register(concept_id="cap-sql-exec", actor="agent_1")

# Switch to production mode for collusion resistance
engine.set_production_mode()  # N_min ≥ 2 distinct validators

# Single-agent validation is now rejected
try:
    engine.transition("cap-sql-exec", to="validated", actor="agent_1", confidence=0.9)
except Exception as e:
    print(f"Rejected: {e}")  # Not enough distinct validators

# A second distinct agent must validate
engine.transition("cap-sql-exec", to="validated", actor="agent_2", confidence=0.8)
print(engine.chains["cap-sql-exec"].status)  # VALIDATED
```

</details>

<details>
<summary><b>Confidence calibration strategies</b></summary>

```python
from adl_lite import parse_file

doc = parse_file("examples/weather_data_retrieval.md")
chain = doc.event_chain

# Four calibration strategies — each answers "how confident are we?" differently:

# 1. G-Counter max (default, O(1)) — highest single-validator confidence
print(chain.confidence)                    # 0.85

# 2. Aggregated confidence — per-actor maxima + quorum bonuses
print(chain.aggregated_confidence())       # γ_agg

# 3. EWMA confidence — time-decayed weighted average (α configurable)
print(chain.ewma_confidence(alpha=0.3))    # γ_ewma

# 4. Band-calibrated confidence — epistemic over/under-correction
print(chain.band_calibrated_confidence())  # γ_band
```

</details>

<details>
<summary><b>Semantic Web exports (OWL, JSON-LD, RDF-star)</b></summary>

```python
from adl_lite import (
    parse_file, export_owl, export_jsonld,
    document_to_rdfstar_turtle, validate_adl_document,
)

doc = parse_file("examples/weather_data_retrieval.md")

# OWL 2 DL export (RDF/XML or Turtle) — load into Protégé
owl_ttl = export_owl(doc, format="turtle")

# JSON-LD export — semantic-web APIs and graph databases
jsonld = export_jsonld(doc)

# RDF-star / SPARQL-star — annotated triple provenance
rdfstar = document_to_rdfstar_turtle(doc)

# Runtime SHACL validation
shacl_errors = validate_adl_document(doc)
print(f"SHACL errors: {len(shacl_errors)}")
```

</details>

<details>
<summary><b>Transparency anchors & Merkle batch proofs</b></summary>

```python
from adl_lite import parse_file
from adl_lite.key_registry import TransparencyAnchor

doc_a = parse_file("examples/weather_data_retrieval.md")
doc_b = parse_file("examples/capital_reflux_trap.md")
chain_a, chain_b = doc_a.event_chain, doc_b.event_chain

# Anchor multiple chains using a Merkle root
anchor = TransparencyAnchor("ANCHOR.md")
value = anchor.anchor([chain_a, chain_b], use_merkle=True, proofs_dir="./proofs")
print(f"Merkle root: {value[:16]}...")

# Generate and verify an individual inclusion proof
proof = anchor.prove_inclusion(chain_a)
assert anchor.verify_inclusion(chain_a, proof)

# Batch verify all chains against the Merkle root (O(log n) per chain)
results = TransparencyAnchor.verify_batch(
    [chain_a, chain_b],
    merkle_root=value,
    proofs={"weather-data-retrieval": proof_a, "disc-capital-trap": proof_b},
)
print(results)  # {'weather-data-retrieval': True, 'disc-capital-trap': True}
```

</details>

### CLI

```bash
# ── Validate ──────────────────────────────────────────────
adl-lite validate examples/*.md                 # Basic validation
adl-lite validate --strict examples/*.md        # + predicate-semantic checks
adl-lite validate --strict-template examples/*.md  # + L2 template enforcement

# ── Parse (dump parsed structure as JSON) ─────────────────
adl-lite parse examples/capital_reflux_trap.md

# ── Consensus (capability lifecycle) ──────────────────────
adl-lite consensus register examples/capital_reflux_trap.md
adl-lite consensus transition disc-capital-trap --to validated --actor agent_1

# ── Ontology query ───────────────────────────────────────
adl-lite ontology query --json

# ── Transparency anchor ──────────────────────────────────
adl-lite anchor                                 # Flat anchor
adl-lite anchor --merkle --proofs-dir ./proofs  # Merkle root + per-chain proofs
adl-lite verify-anchor                          # Verify flat anchor
adl-lite verify-anchor --state ./state.json     # Verify from saved state
adl-lite verify-batch --anchor ANCHOR.md --proofs-dir ./proofs  # Merkle batch verification

# ── LLM normalization (dry-run by default) ───────────────
adl-lite normalize --input-dir ./concepts --threshold 0.92
adl-lite normalize --input-dir ./concepts --threshold 0.92 --execute
```

### Python API

```python
from adl_lite import parse_file, Event, EventChain, EventType
from adl_lite.action_executor import ActionExecutor
from adl_lite.ontology import OntologyManager

# Event chain
doc = parse_file("examples/capital_reflux_trap.md")
chain = doc.event_chain
print(chain.status)                    # Derived from chain
print(chain.confidence)                # O(1) — G-Counter max over VALIDATE events
print(chain.aggregated_confidence())   # Bonus-formula aggregate
print(chain.history())                 # Full audit log

# Action execution
mgr = OntologyManager()
executor = ActionExecutor(mgr)
errors = executor.validate_action(doc, action_block)

# Consensus engine with dev/production mode
from adl_lite.consensus import ConsensusEngine
engine = ConsensusEngine(ontology=mgr, dev_mode=True)   # N_min=1 (dev)
engine.set_production_mode()                              # N_min≥2 (collusion resistance)
engine.register(concept_id="cap-weather-api", actor="agent_1")
engine.transition(concept_id="cap-weather-api", to="validated", actor="agent_2")

# Data import (IBM AML stress test)
from adl_lite.data_importer import DataImporter
chains = DataImporter().import_csv("HI-Small_Trans.csv",
    event_type=EventType.REGISTER, concept_id_field="Account")

# DID signature verification
from adl_lite import KeyRegistry
registry = KeyRegistry()
chain.verify_integrity(registry=registry)  # Verify Ed25519 / secp256k1 signatures

# OWL / JSON-LD / RDF-star export
from adl_lite import export_owl, export_jsonld, document_to_rdfstar_turtle
owl_ttl = export_owl(doc, format="turtle")
jsonld = export_jsonld(doc)
rdfstar = document_to_rdfstar_turtle(doc)

# SHACL validation
from adl_lite import validate_adl_document
shacl_errors = validate_adl_document(doc)

# L3 Relation validation
from adl_lite import RelationValidator
validator = RelationValidator()
valid = validator.valid(relation, source_status, target_status)

# Near-duplicate detection
from adl_lite import check_near_duplicate, suggest_merge
matches = check_near_duplicate(doc, existing_chains, threshold=0.85)
merge_suggestion = suggest_merge(doc, existing_chains)

# Vector semantic search
from adl_lite import VectorIndex, SentenceTransformerBackend
index = VectorIndex(backend=SentenceTransformerBackend())
index.add(doc.adl_id, doc.markdown_body)
results = index.search("gradient explosion", top_k=5, threshold=0.8)

# LLM normalization (dry-run)
from adl_lite import CanonicalizationEngine, OpenAILLMBackend
engine = CanonicalizationEngine(index, llm=OpenAILLMBackend())
proposals = engine.normalize(threshold=0.92, dry_run=True)

# Merkle transparency anchor
from adl_lite import MerkleTree, compute_chain_merkle_root
root = compute_chain_merkle_root(chain)
proof = MerkleTree.generate_proof(chain.events, target_event_hash)

# N≥3 CRDT chain merge (Complete Version)
from adl_lite.crdt import merge_event_chains
merged = merge_event_chains(chain_a, chain_b, chain_c, chain_d)  # N-way merge via pairwise fold

# Merkle batch verification (Complete Version)
from adl_lite.key_registry import TransparencyAnchor
results = TransparencyAnchor.verify_batch(chains, merkle_root, proofs)  # → {concept_id: bool}

# Linked Data Proofs
from adl_lite import create_event_proof, verify_event_proof
event = chain.events[-1]
proof = create_event_proof(event, did="did:key:z6Mk...", registry=registry)
assert verify_event_proof(event, proof, registry=registry)
```

### REST API

```bash
# Start the API server
uvicorn adl_lite.api:app --reload --port 8000

# Register a concept
curl -X POST http://localhost:8000/api/v1/consensus/register \
  -H "Content-Type: application/json" \
  -d '{"adl_id": "cap-weather-api", "actor": "agent_1", "domain": "weather", "scope": "public"}'

# Validate (transition to validated)
curl -X POST http://localhost:8000/api/v1/consensus/transition \
  -H "Content-Type: application/json" \
  -d '{"adl_id": "cap-weather-api", "to": "validated", "actor": "agent_2", "confidence": 0.85}'

# Check status
curl http://localhost:8000/api/v1/consensus/status/cap-weather-api

# Fork a concept
curl -X POST http://localhost:8000/api/v1/consensus/fork \
  -H "Content-Type: application/json" \
  -d '{"adl_id": "cap-weather-api", "child_id": "cap-weather-api-v2", "actor": "agent_3"}'

# Switch to production mode (N_min ≥ 2)
curl -X POST http://localhost:8000/api/v1/consensus/mode/production

# Switch back to dev mode (N_min = 1)
curl -X POST http://localhost:8000/api/v1/consensus/mode/dev
```

Once the server is running, interactive API docs are available at
`http://localhost:8000/docs` (Swagger UI).

---

## Architecture

```
Markdown capability file (L1/L2/L3/L4)
        ↓
ADLParser → ADLDocument + EventChain
        ↓
OntologyManager ← adl_core_ontology.yaml (classes / predicates / actions / transitions)
        ↓
ActionExecutor (precondition validation + side effects + EWMA calibration)
        ↓
ConsensusEngine (append-only transition chain + ForkManager + dev_mode / production N_min)
        ↓
ADLMemory (Hot skeleton / Warm SQLite+NetworkX / Cold archive)
  ┌─────┴──────────────────────────────────────────────┐
  │  WarmIndex degradation (BD-02): SQLite timeout >5s → HotIndex fallback │
  └─────────────────────────────────────────────────────┘
        ↓
RelationValidator (L3 relation integrity + Invariant 2)
        ↓
FastAPI REST API (/api/v1/consensus/) ← uvicorn → external clients
```

### Four-Layer Document Model

| Layer | Syntax | Role | Event Type |
|-------|--------|------|-------------|
| L1 | YAML front matter | Identity metadata (derived snapshot) | SNAPSHOT |
| L2 | Markdown body | Human/LLM narrative | — |
| L3 | `adl:relation/evidence/seal` | Typed semantic assertions | RELATE, EVIDENCE, SEAL |
| L4 | `adl:action` | Typed actions with preconditions | REGISTER, VALIDATE, ... |

### Event-First Design

```python
from adl_lite import Event, EventChain, EventType, DiscoveryStatus

chain = EventChain(concept_id="cap-weather-api")

chain.append(Event(concept_id="cap-weather-api",
                   event_type=EventType.REGISTER,
                   actor="agent_1"))

chain.append(Event(concept_id="cap-weather-api",
                   event_type=EventType.VALIDATE,
                   actor="agent_2",
                   payload={"confidence": 0.85}))

# Status derived from chain, NOT stored
assert chain.status == DiscoveryStatus.VALIDATED
assert chain.confidence == 0.85
assert chain.verify_integrity()  # SHA-256 hash verification
```

### Consensus States

```
provisional → validated → deprecated → archived
                 ↓
              forked (parent retains validated)
```

| provisional | validated | deprecated | forked | archived |
|:---:|:---:|:---:|:---:|:---:|

Status transitions are monotonic (CRDT LUB semantics): a concept never regresses
to a lower-status state once it has reached a higher one.

---

## Core Concepts

| Term | Definition |
|------|-----------|
| **EventChain** | Append-only, cryptographically hash-linked event sequence. Capability = chain. |
| **Event** | Atomic event: event_type, actor, payload, hash, previous_event_id, canon_version |
| **Event-first** | Status/confidence/validators derived from chain, no mutable fields stored |
| **Capability** | A claim an agent makes: "I can retrieve weather data", "I can execute SQL" |
| **δ(C)** | Deterministic status derivation function (O(1)) |
| **γ(C)** | G-Counter max confidence over all VALIDATE / SNAPSHOT events |
| **γ_agg(C)** | Bonus-formula aggregate: per-actor maxima + quorum bonuses |
| **γ_cal(C)** | Per-actor accuracy-weighted calibrated confidence |
| **γ_ewma(C)** | EWMA-calibrated confidence with time-decay (α configurable, default 0.3) |
| **γ_ctx(C)** | Per-domain context-calibrated confidence (e.g., AML vs fraud vs general) |
| **γ_band(C)** | Epistemic-band calibrated confidence (over/under-correction) |
| **Action Type** | L4 blocks: declarative actions + Comparator preconditions (no eval()) |
| **Trust Model** | Hash chain integrity + canonicalization version + Ed25519/DIDs + Merkle proofs |
| **Relation Validator** | Invariant 2: L3 relation validity based on endpoint lifecycle status |
| **RDF-star** | Embedded triple annotations for event provenance in triple stores |
| **SHACL** | Runtime shape validation over ADLDocument concepts, events, and relations |
| **Vector Index** | FAISS-backed semantic search over ADL Markdown bodies |
| **Canonicalization** | LLM-driven clustering and normalization of near-duplicate concepts |
| **REST API** | FastAPI `/api/v1/consensus/` endpoints for external lifecycle management |
| **dev_mode** | ConsensusEngine dev mode: N_min=1 (single validator) vs production N_min≥2 (collusion resistance) |
| **WarmIndex degradation** | BD-02: SQLite timeout >5s → degrade to HotIndex (ConceptSkeleton) with auto-recovery |

### Agent Governance Positioning

ADL Lite is a **complementary governance layer**, not a competing ontology production method:

| System | Answers | Layer |
|--------|---------|-------|
| **KYA** | "Is this agent trusted?" | Permissions / trust |
| **AgentSafe** | "Is this architecture safe?" | Design-time + runtime + audit |
| **Talukdar et al.** | "How do we build ontologies with agents?" | Ontology production |
| **"Agent Traces to Trust"** | "How do we trace what agents did?" | Provenance |
| **SafeAgent** | "Is this agent dangerous?" | Safety protocol |
| **ADL Lite** | "How do we record, validate, and govern capabilities?" | **Capability lifecycle registry** |

A complete agent ecosystem uses **KYA** for permissions, **AgentSafe** for architecture safety, and **ADL Lite** for capability lifecycle governance.

---

## Experiments

**paper_ao** (architectural correctness + boundary conditions):

| # | Experiment | Key Metric |
|---|-----------|-----------|
| E1 | Chain integrity | 60 chains: P=R=F1=1.0 |
| E2 | Status derivation | 2,204 cases: 100% correct |
| E3 | Snapshot round-trip | 212/212 files: 100% pass |
| E4 | Precondition enforcement | 141 cases: P=R=F1=1.0 |
| E5 | 5-agent audit | ConsensusEngine + harness simulation |
| E6 | IBM AML pipeline (architectural stress test) | 201 chains, 9,300 events, 100% integrity |
| E7 | Real-time watcher | Event stream ingestion |
| E8 | Edge sync | Edge-to-core sync coordination |
| E9 | Git baseline | Parser + consensus integrity |
| E10 | FDE pipeline | OntologyManager + ActionExecutor |
| E11 | Side-effect stress | ActionExecutor + side effects |
| E12 | Benchmark comparison | Cross-format throughput comparison |
| E13 | Long-chain stress | Linear to 50k events, R² = 1.0 |
| E14 | Collusion vulnerability | 1 actor → γ = 0.99 (Phase 1 limitation) |
| E15 | Precondition boundary | 4/11 caught by Pydantic (defense-in-depth gap) |
| E16 | Contention simulation | 95% rejection at k=20 (no fork-on-conflict) |
| E17 | Multi-agent collaboration | Collaborative capability registration patterns |
| E19 | Governance benchmark | Formal governance metrics across 100+ concepts |
| E20 | Template effectiveness | 100% section coverage |
| E20b | Calibration baseline | ECE reduction 4.10× |
| E21 | 100k event stress | Linear scaling, memory < 1GB |
| E23 | Concurrent agent contention | 50 agents, 0 integrity failures |
| E24 | Proof trace checker (randomized) | 10,000 synthetic chains: T1–T7 validated |
| E25 | Microbenchmark | Precondition eval + confidence aggregation |
| E27 | 1M event scale test | Split-lock + incremental verify + zstd cold storage |
| E28 | 10k concurrent agent contention | Split-lock throughput under 10k agents |
| E29 | Vector index recall | FAISS ANN recall vs brute-force cosine |
| E30 | LLM normalization | Dry-run LLM canonicalization of near-duplicates |

Run experiments:

```bash
# List all available experiments
python -m experiments.runner list

# Run a single experiment
python -m experiments.runner E2 --verbose

# Run all experiments (5–15 minutes)
python -m experiments.runner all

# One-command reproduction script
./reproduce.sh              # all core experiments
./reproduce.sh quick        # E1–E4 + E24 only (~30 seconds)
./reproduce.sh docker       # build & run Docker image
./reproduce.sh test         # pytest suite only
```

---

## Project Structure

```
adl-lite/
├── adl_lite/              # Main package
│   ├── __init__.py        # Public API exports
│   ├── models.py          # Event, EventChain, ADLDocument, PreconditionRule
│   ├── parser.py          # L1/L2/L3/L4 parser
│   ├── validator.py       # SSA validation + scope ACL + relation governance
│   ├── consensus.py       # Consensus chain + fork + dynamic N_min (dev_mode / production)
│   ├── action_executor.py # Action execution + precondition checking + side effects + EWMA calibration
│   ├── api.py             # FastAPI REST API (/api/v1/consensus/)
│   ├── data_importer.py   # CSV/JSON → Event import
│   ├── ontology.py        # OntologyManager (predicates/actions/transitions)
│   ├── memory.py          # Hot/Warm/Cold index with optional VectorIndex + WarmIndex degradation
│   ├── tools.py           # Agent tool wrappers
│   ├── crdt.py            # CRDT merge semantics + LWW-Set N≥3 EventChain merge (Theorem 9)
│   ├── calibration.py     # MARGINCalibrator + γ_agg / γ_cal / γ_ewma / γ_band
│   ├── embeddings.py      # Pluggable embedding backends (SentenceTransformer / OpenAI)
│   ├── vector_index.py    # FAISS-backed persisted vector index + semantic search
│   ├── canonicalization.py # LLM-driven normalization: cluster → propose → emit ADL actions
│   ├── owl_export.py      # OWL 2 DL export (RDF/XML + Turtle)
│   ├── owl_import.py      # OWL 2 DL import (Turtle + RDF/XML round-trip)
│   ├── jsonld_export.py   # JSON-LD export
│   ├── rdfstar_export.py  # RDF-star / SPARQL-star export for annotated triples
│   ├── prov_export.py     # PROV-O provenance serialization
│   ├── shacl_validation.py # Runtime SHACL validation over ADLDocument
│   ├── near_duplicate.py  # Near-duplicate detection (Jaccard / Levenshtein / embeddings)
│   ├── realtime.py        # Real-time event watcher
│   ├── sync_manager.py    # Edge-to-core sync coordination
│   ├── did_resolver.py    # Multi-method DID resolver (did:key / did:web / did:ethr)
│   ├── key_registry.py    # Key registry + transparency anchor + Merkle batch verify + Git sigs
│   ├── ld_proof.py        # W3C Linked Data Proofs (Ed25519 / secp256k1)
│   ├── merkle.py          # SHA-256 Merkle trees with inclusion proofs
│   ├── relation_validator.py # L3 Relation Reconciliation (Invariant 2)
│   ├── cold_storage.py    # zstd+msgpack compressed cold storage + archive
│   ├── l2_template.py     # L2 template schema + validation
│   ├── cli.py             # adl-lite CLI entry point
│   ├── logging_config.py  # Structured logging
│   ├── exceptions.py      # ADL exception hierarchy
│   ├── fde/               # MVP FDE platform (pipeline, importer, tenant, rule engine, agent runner)
│   └── adl_core_ontology.yaml # v0.2: classes + predicates + actions + collusion_resistance
├── experiments/
│   ├── base.py            # BaseExperiment + ExperimentResult
│   ├── registry.py        # @register("E1") decorator
│   ├── runner.py          # python -m experiments.runner all
│   ├── harness.py         # 5-agent simulation harness
│   ├── proof_trace_checker.py # Randomized property-based theorem validation
│   └── e*.py              # 28 registered experiments (E1–E30)
├── tests/                 # pytest suite (1358 pass, 6 skip, 87% coverage)
├── examples/              # Capability file examples
├── data/aml/              # AML domain stress test data
├── docs/
│   ├── paper_ao/          # Applied Ontology journal submission (51pp)
│   ├── experiments/       # Current experiment results
│   ├── incident-management/ # Runbooks & SLOs
│   ├── ontology/          # Current ontology artifacts
│   ├── AGENT_WORKFLOW.md  # 8-step agent workflow
│   ├── CODE_REVIEW_STANDARDS.md
│   ├── CRDT_MIGRATION_GUIDE.md
│   └── verification_status.md # Theorem/Coq/TLA+ verification status
├── specs/                 # TLA+ formal specifications
├── formal/coq/            # Buildable Coq/Iris proof skeleton
├── scripts/               # Utility scripts (TLC wrapper, etc.)
├── reproduce.sh           # One-command reproduction script
├── archive/               # Deprecated files (excluded from lint)
├── pyproject.toml         # Package config, ruff, mypy
├── Dockerfile             # Reproducibility environment
├── .github/workflows/ci.yml
└── .pre-commit-config.yaml
```

---

## Paper Status

| Item | Status |
|------|--------|
| **paper_ao/** | Applied Ontology journal — under major revision (39 pp, 30+ refs, 9 theorems) |
| **Target venue** | Applied Ontology (ESWC/ISWC 2027 track as backup) |
| **New title** | *ADL Lite: An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems* |
| **Key framing** | Complementary governance layer — not a competing ontology production method |

**Key properties (formalised in paper_ao Section 4):**

| Theorem | Property |
|---------|----------|
| T1 | Determinism of δ(C) |
| T2 | Confluence under fork |
| T3 | Status transition monotonicity |
| T4 | Confidence boundedness γ(C) ∈ [0,1] |
| T5 | Confidence monotonicity under **non-colluding** validation |
| T6 | Status–confidence consistency (δ = validated ⟹ γ ≥ 0.5) |
| T7 | CRDT convergence under LWW-Set merge |
| Corollary | Event-level G-Set CRDT |

---

## Roadmap

| Status | Item | Description |
|--------|------|-------------|
| ✅ v0.2.0 | Event-first core | EventChain, 12 axioms, CRDT merge, 9 theorems |
| ✅ v0.2.0 | Calibration | γ, γ_agg, γ_cal, γ_ewma, γ_ctx, γ_band |
| ✅ v0.2.0 | DID & signatures | did:key, Ed25519, KeyRegistry, transparency anchors |
| ✅ v0.2.0 | Semantic Web | OWL bidirectional, RDF-star, SPARQL-star, JSON-LD |
| ✅ v0.2.0 | L3 governance | RelationValidator, Invariant 2, fork inheritance |
| 🔄 Active | Paper revision | Major revision for Applied Ontology (51pp, 9 theorems, TLA⁺ + Coq) |
| ✅ v0.6.0-alpha | Complete version | N≥3 CRDT merge (Theorem 9), Merkle batch verification, DID complete, `verify-batch` CLI |
| ✅ v0.5.0-alpha | Formal methods | TLA⁺ bounded specs, Coq/Iris skeleton, proof trace checker |
| ✅ v0.5.0-alpha | Scale architecture | Split-lock, incremental verify, zstd+msgpack cold storage |
| ✅ v0.5.0-alpha | REST API | FastAPI /api/v1/consensus/ endpoints, dev/production mode toggle |
| ✅ v0.5.0-alpha | Architecture dev | N_min dynamic threshold, EWMA side-effect, WarmIndex degradation, CLI fixes |
| ✅ v0.4.2-alpha | Vector + LLM | Embeddings, FAISS vector index, LLM canonicalization (E29/E30) |
| ✅ v0.4.1-alpha | Cold storage | zstd+msgpack compressed archival, auto-archival in ADLMemory |
| ✅ v0.4.0-alpha | Full DID suite | did:web, did:ethr, LD-Proofs, Merkle trees |
| ✅ v0.4.0-alpha | SHACL validation | Runtime shape validation |
| ✅ v0.4.0-alpha | Expert calibration | Auto domain-expert calibration, EWMA accuracy tracking |
| ✅ v0.4.0-alpha | Dynamic collusion | Ontology-driven N_min enforcement |
| ✅ v0.3.5 | CRDT migration | LUB status + G-Counter confidence (status never regresses) |

---

## Contributing

Contributions are welcome! This project follows a standard fork-and-PR workflow.

### Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/adl-lite.git
cd adl-lite

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 4. Install pre-commit hooks (auto-runs ruff + mypy on every commit)
pip install pre-commit
pre-commit install
```

### Code Style

| Tool | Configuration | Command |
|------|---------------|---------|
| **ruff** | Line length 100, target py310, rules E/F/W/I/N/UP/B/C4 | `ruff check adl_lite/` |
| **ruff-format** | Enforced in CI and pre-commit | `ruff format adl_lite/` |
| **mypy** | `--ignore-missing-imports`, untyped defs allowed | `mypy adl_lite/ --ignore-missing-imports` |

Key conventions:
- **Line length**: 100 characters (enforced by ruff)
- **Target Python**: 3.10 (use no syntax newer than 3.10 in `adl_lite/`)
- **Comments & docstrings**: English
- **User-facing CLI output**: Bilingual (English/Chinese) is OK
- **File naming**: test files match `test_<module>.py`
- **Excluded from lint**: `archive/`, `data/aml/scripts/`

### Running Tests

```bash
# Fast test suite (excludes slow benchmarks — ~6 seconds)
pytest tests/ -m "not slow" -v

# Full test suite with coverage
pytest tests/ -v --cov=adl_lite --cov-report=xml --cov-report=term-missing

# Run a specific test file
pytest tests/test_consensus.py -v

# Run a single test
pytest tests/test_consensus.py::test_register -v
```

**Test markers:**
- `@pytest.mark.slow` — marks long-running tests (benchmarks, stress tests).
  Exclude with `-m "not slow"` for fast iteration.
- `asyncio_mode = "auto"` — async tests run without explicit markers.

### Pre-Commit Hooks

The `.pre-commit-config.yaml` runs **ruff** (lint + format) and **mypy** on every
commit. If a hook fails, fix the reported issues and re-stage:

```bash
# Run all hooks manually
pre-commit run --all-files

# If ruff auto-fixes issues, re-stage the changed files
git add -u && git commit
```

### Submitting a Pull Request

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes**. Ensure all checks pass:
   ```bash
   ruff check adl_lite/
   ruff format --check adl_lite/
   mypy adl_lite/ --ignore-missing-imports
   pytest tests/ -m "not slow" -v
   ```

3. **Add tests** for new functionality. Aim to maintain or improve coverage
   (current target: ≥ 85%).

4. **Commit with a clear message**. We follow [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat: add did:pkh resolver support
   fix: handle None payload in EWMA calibration
   docs: update installation instructions
   test: add fork inheritance edge cases
   refactor: extract merkle proof verification
   ```

5. **Push and open a PR** against `main`. Include:
   - A summary of what changed and why
   - Any breaking changes (mark with `BREAKING CHANGE:`)
   - Test results or experiment output if applicable

### CI Pipeline

Every push and PR to `main` triggers [GitHub Actions](.github/workflows/ci.yml)
which runs on Python 3.10, 3.11, and 3.12:

1. **Install** — `pip install -e ".[dev]"`
2. **Test** — `pytest tests/ -v --cov=adl_lite --cov-report=xml`
3. **Lint** — `ruff check adl_lite/`
4. **Type check** — `mypy adl_lite/ --ignore-missing-imports`
5. **Benchmark** — `python experiments/benchmarks/throughput.py`
6. **Coverage** — uploaded to Codecov (Python 3.12 job only)

All steps must pass for the PR to be mergeable.

### Reporting Issues

- **Bugs**: Open an issue with a minimal reproduction (code snippet + expected
  vs. actual output + Python version + OS).
- **Feature requests**: Describe the use case and proposed API surface.
- **Security vulnerabilities**: Do NOT open a public issue. Email the
  maintainers directly.

---

## License

MIT License — see [LICENSE](LICENSE).

Copyright (c) 2026 CEIEC AI Infrastructure.
