# ADL Lite — An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ESWC/ISWC 2027 Backup](https://img.shields.io/badge/Backup-ESWC%2FISWC%202027-blue.svg)](https://2027.eswc-conferences.org/)
[![Applied Ontology: under revision](https://img.shields.io/badge/Journal-Applied%20Ontology-orange.svg)](https://www.iospress.nl/journal/applied-ontology/)
[![Tests: 1039 PASS](https://img.shields.io/badge/tests-1039%20PASS-brightgreen.svg)]()
[![Coverage: 87.8%](https://img.shields.io/badge/coverage-87.8%25-brightgreen.svg)]()
[![Release Readiness: GO](https://img.shields.io/badge/release%20readiness-GO-brightgreen.svg)]()
[![API: FastAPI](https://img.shields.io/badge/API-FastAPI%20REST-009688.svg)]()
[![Paper: 39pp](https://img.shields.io/badge/paper-39pp-blue.svg)]()

> **"The world is the totality of facts, not of things." — Wittgenstein, Tractatus Logico-Philosophicus §1.1**

ADL Lite is an **event-first, Markdown-native capability-lifecycle registry** for LLM agent ecosystems. Each capability (tool, API, knowledge domain) is represented as an **append-only, cryptographically hash-linked EventChain**. Status, confidence, and validators are **never stored as mutable fields** — all derived deterministically from the event history.

ADL Lite fills the gap between **KYA** (permissions layer) and **AgentSafe** (architecture-level governance): a lightweight, verifiable registry that records what agents can do, how capabilities evolve, and whether they remain trustworthy.

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
| T1 | Determinism of $\delta(C)$ |
| T2 | Confluence under fork |
| T3 | Status transition monotonicity |
| T4 | Confidence boundedness $\gamma(C) \in [0,1]$ |
| T5 | Confidence monotonicity under **non-colluding** validation |
| T6 | Status–confidence consistency ($\delta = $ validated $\implies \gamma \geq 0.5$) |
| T7 | CRDT convergence under LWW-Set merge |
| Corollary | Event-level G-Set CRDT |

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
| E13 | Long-chain stress | Linear to 50k events, $R^2 = 1.0$ |
| E14 | Collusion vulnerability | 1 actor → $\gamma = 0.99$ (Phase 1 limitation) |
| E15 | Precondition boundary | 4/11 caught by Pydantic (defense-in-depth gap) |
| E16 | Contention simulation | 95% rejection at $k=20$ (no fork-on-conflict) |
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

## New in v0.5.0-alpha (This Release)

### Architecture-Driven Development
- **FastAPI REST API** (`adl_lite/api.py`) — `/api/v1/consensus/` endpoints: register, transition, status, history, fork, verify, list, mode (dev/production)
- **ConsensusEngine dev_mode** — `dev_mode=True` default (N_min=1 for development); `set_production_mode()` switches to N_min≥2 for collusion resistance
- **EWMA calibration side-effect** — VALIDATE transition automatically triggers `MARGINCalibrator.update_accuracy_ewma()` for continuous confidence calibration
- **WarmIndex degradation** (BD-02) — SQLite I/O timeout >5s → degrade to HotIndex (ConceptSkeleton only), with auto-recovery
- **CLI bug fixes** — `ADLOntologyError` catch in ontology query/validate; `verify-anchor --state` loads chains from state file for integrity verification
- **Optional-dep test guards** — graceful `pytest.mark.skipif` for sentence-transformers, faiss, zstandard, msgpack

### Test & Coverage Improvement (v0.5.0-alpha)
- **Test count**: 796 → **1057** → **1039 fast suite** (+261 tests, +32.8%; 22 skipped for optional deps)
- **Code coverage**: 75.5% → **87.8%** (full suite), **83%** (fast suite)
- **FDE module coverage**: 0% → **96.9%** (rule_engine, pipeline_engine, agent_runner, importers, transformers)
- **Zero-coverage modules eliminated**: 7 → 0
- **CI coverage gate**: configured (min 75%, target 85%)
- **Slow test markers**: `@pytest.mark.slow` on 17 long-running tests (3.3× fast-test speedup)

### Formal Methods & Verification
- **TLA+ bounded specifications** — `specs/EventChain.tla` (single chain: T1/T2/T3/T4/T5/T7), `specs/CRDTMerge.tla` (two-branch merge: T9), `specs/ConsensusEngine.tla` (multi-agent with `N_min` validators: T6/T8)
- **Buildable Coq/Iris skeleton** — `formal/coq/` with closed proofs for `Status.v`, `Event.v`, `Confidence.v`, `Chain.v`, `Invariants.v`, `CRDT.v` (Theorem 9 fully closed); Iris ghost-state stubs for split-lock concurrency
- **Proof trace checker** — `proof_trace_checker.py` randomized property-based validation of Theorems 1–7 over 10,000 synthetic chains (E24)

### Scale & Performance
- **Split-lock EventChain** — `_events_lock` + `_cache_lock` (RLock) targeting 10k concurrent agents
- **Incremental integrity verification** — caches verified prefix, only validates newly appended events
- **zstd+msgpack cold storage** — compressed archival in `cold_storage.py` with streaming decompression
- **1M event scale** — linear append/verify throughput with memory < 2 GB (E27)
- **10K concurrent agent contention** — split-lock throughput under 10k logical agents (E28)
- **Microbenchmark** — precondition eval time vs rule count and confidence aggregation time vs validator count (E25)

### Vector Index & LLM Normalization
- **Pluggable embedding backends** — `SentenceTransformerBackend` (local-first) and `OpenAIBackend`
- **FAISS-backed vector index** — persisted semantic search with pre-filtering, SQLite metadata backup, thread-safe RLock
- **LLM-driven canonicalization** — `CanonicalizationEngine` clusters near-duplicates, proposes canonical forms, emits auditable ADL action blocks; dry-run by default (E30)
- **Vector index recall** — FAISS ANN recall against brute-force cosine (E29)
- **New CLI**: `adl-lite normalize --input-dir ./concepts --threshold 0.92 --dry-run`

### Security, Trust & Identity
- **Multi-method DID resolver** — `did:key`, `did:web` (HTTPS), `did:ethr` (ecrecover via optional `[did]` extras)
- **Linked Data Proofs** — `create_event_proof()` / `verify_event_proof()` with `Ed25519Signature2020` and `EcdsaSecp256k1Signature2019`; `Event.proof` field stores W3C Data Integrity proofs
- **Merkle batch verification** — `MerkleTree` with SHA-256, inclusion proofs, and per-chain transparency anchors
- **Transparency anchor** — flat and Merkle root anchors with inclusion proofs; CLI: `adl-lite anchor --merkle --proofs-dir <dir>` and `adl-lite verify-inclusion <adl_id>`

### Governance & Validation
- **Runtime SHACL validation** — `validate_adl_document()` runs built-in shapes on ADLDocument (Concept, Event, Agent, Relation, CalibrateEvent)
- **Auto domain-expert calibration** — `MARGINCalibrator.update_accuracy_ewma()` + `apply_calibration_event()` + `update_from_feedback()`; `calibrate` action wired to `ActionExecutor` side effects
- **Dynamic collusion resistance** — `OntologyManager.min_distinct_validators()` reads from ontology YAML; enforced by `ConsensusEngine` and `ActionExecutor`
- **L3 Relation governance** — `RelationValidator` enforces Invariant 2 (lifecycle-based validity) with optional strict predicate-semantic checks and `status_resolver` callback

### Semantic Web Interoperability
- **OWL 2 bidirectional** — `export_owl()` + `parse_owl_turtle()` / `parse_owl_rdfxml()` for round-trip Protégé interoperability
- **RDF-star / SPARQL-star** — `document_to_rdfstar_turtle()` and `sparqlstar_query_template()` for annotated triple provenance
- **JSON-LD export** — `export_jsonld()` for semantic-web APIs and graph databases
- **PROV-O export** — `prov_export.py` for provenance serialization

### Test & Experiment Coverage
- **1039 tests passing** (22 skipped for optional deps), 87.8% coverage (full suite), 83% coverage (fast suite)
- **28 registered experiments** (E1–E30, excluding E17/E18/E22/E26) — covering chain integrity, status derivation, snapshot round-trip, precondition enforcement, 5-agent audit, AML pipeline, real-time watcher, edge sync, git baseline, FDE pipeline, side-effect stress, governance benchmark, long-chain stress, collusion, contention, proof trace, microbenchmark, 1M scale, 10k concurrency, vector index recall, and LLM normalization

## Quick Start

```bash
git clone https://github.com/sunnyang1/adl-lite.git
cd adl-lite
pip install -e ".[dev]"

# Run all experiments
python -m experiments.runner all

# List experiments
python -m experiments.runner list

# Run single
python -m experiments.runner E2

# Run tests (1039 passed, 87.8% coverage)
pytest tests/ -v --cov=adl_lite --cov-report=term-missing

# Run fast tests only (excludes slow benchmarks)
pytest tests/ -m "not slow" -v --cov=adl_lite

# Start the REST API server
uvicorn adl_lite.api:app --reload --port 8000
```

### CLI

```bash
# Validate
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md
adl-lite validate --strict-template examples/*.md

# Parse
adl-lite parse examples/capital_reflux_trap.md

# Consensus (capability lifecycle)
adl-lite consensus register examples/capital_reflux_trap.md
adl-lite consensus transition disc-capital-trap --to validated --actor agent_1

# Ontology query
adl-lite ontology query --json

# Transparency anchor
adl-lite anchor
adl-lite anchor --merkle --proofs-dir ./proofs
adl-lite verify-anchor
adl-lite verify-anchor --state ./state.json
adl-lite verify-inclusion <adl_id> --proof ./proofs/<adl_id>.json

# Normalization (dry-run by default)
adl-lite normalize --input-dir ./concepts --threshold 0.92
adl-lite normalize --input-dir ./concepts --threshold 0.92 --execute
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

### Python API

```python
from adl_lite import parse_file, Event, EventChain, EventType
from adl_lite.action_executor import ActionExecutor
from adl_lite.ontology import OntologyManager

# Event chain
doc = parse_file("examples/capital_reflux_trap.md")
chain = doc.event_chain
print(chain.status)           # Derived from chain
print(chain.confidence)       # O(1) — G-Counter max over VALIDATE events
print(chain.aggregated_confidence())  # Bonus-formula aggregate
print(chain.history())        # Full audit log

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

# Calibration (4 strategies)
print(chain.confidence)                  # O(1) — G-Counter max
print(chain.aggregated_confidence())       # γ_agg — bonus-formula
print(chain.ewma_confidence(alpha=0.3))   # γ_ewma — time-decay
print(chain.band_calibrated_confidence())  # γ_band — epistemic correction

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

# Linked Data Proofs
from adl_lite import create_event_proof, verify_event_proof
event = chain.events[-1]
proof = create_event_proof(event, did="did:key:z6Mk...", registry=registry)
assert verify_event_proof(event, proof, registry=registry)
```

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
│   ├── crdt.py            # CRDT merge semantics + LWW-Set EventChain merge
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
│   ├── key_registry.py    # Key registry + transparency anchor + Git signatures
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
│   └── e*.py              # 28 registered experiments (E1–E30, excluding E17/E18/E22/E26)
├── tests/                 # pytest suite (1039 pass, 22 skip, 87.8% coverage)
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

## Core Concepts

| Term | Definition |
|------|-----------|
| **EventChain** | Append-only, cryptographically hash-linked event sequence. Capability = chain. |
| **Event** | Atomic event: event_type, actor, payload, hash, previous_event_id, canon_version |
| **Event-first** | Status/confidence/validators derived from chain, no mutable fields stored |
| **Capability** | A claim an agent makes: "I can retrieve weather data", "I can execute SQL" |
| **$\delta(C)$** | Deterministic status derivation function (O(1)) |
| **$\gamma(C)$** | G-Counter max confidence over all VALIDATE / SNAPSHOT events |
| **$\gamma_{agg}(C)$** | Bonus-formula aggregate: per-actor maxima + quorum bonuses |
| **$\gamma_{cal}(C)$** | Per-actor accuracy-weighted calibrated confidence |
| **$\gamma_{ewma}(C)$** | EWMA-calibrated confidence with time-decay (α configurable, default 0.3) |
| **$\gamma_{ctx}(C)$** | Per-domain context-calibrated confidence (e.g., AML vs fraud vs general) |
| **$\gamma_{band}(C)$** | Epistemic-band calibrated confidence (over/under-correction) |
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

## Agent Governance Positioning

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

## Consensus States

| provisional | validated | deprecated | forked | archived |
|:---:|:---:|:---:|:---:|:---:|

## Roadmap

| Status | Item | Description |
|--------|------|-------------|
| ✅ v0.2.0 | Event-first core | EventChain, 12 axioms, CRDT merge, 9 theorems |
| ✅ v0.2.0 | Calibration | γ, γ_agg, γ_cal, γ_ewma, γ_ctx, γ_band |
| ✅ v0.2.0 | DID & signatures | did:key, Ed25519, KeyRegistry, transparency anchors |
| ✅ v0.2.0 | Semantic Web | OWL bidirectional, RDF-star, SPARQL-star, JSON-LD |
| ✅ v0.2.0 | L3 governance | RelationValidator, Invariant 2, fork inheritance |
| 🔄 Active | Paper revision | Major revision for Applied Ontology (51pp, 9 theorems, TLA⁺ + Coq) |
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

## License

MIT License — see [LICENSE](LICENSE)
