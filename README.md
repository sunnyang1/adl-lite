# ADL Lite — An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ESWC/ISWC 2027 Backup](https://img.shields.io/badge/Backup-ESWC%2FISWC%202027-blue.svg)](https://2027.eswc-conferences.org/)
[![Applied Ontology: under revision](https://img.shields.io/badge/Journal-Applied%20Ontology-orange.svg)](https://www.iospress.nl/journal/applied-ontology/)
[![Tests: 723 PASS](https://img.shields.io/badge/tests-723%20PASS-brightgreen.svg)]()
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
ActionExecutor (precondition validation + side effects)
        ↓
ConsensusEngine (append-only transition chain + ForkManager)
        ↓
ADLMemory (Hot skeleton / Warm SQLite+NetworkX / Cold archive)
        ↓
RelationValidator (L3 relation integrity + Invariant 2)
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

## New in v0.2.0 (This Release)

### Confidence & Calibration
- **Aggregated confidence (`γ_agg`)** — bonus-formula with per-actor maxima and quorum bonuses (Appendix E)
- **Calibrated confidence (`γ_cal`)** — per-actor accuracy-weighted, collusion-mitigating
- **EWMA confidence (`γ_ewma`)** — time-decay weighted calibration with configurable α (0.3 default)
- **Context-calibrated confidence (`γ_ctx`)** — per-domain accuracy profiles (e.g., AML vs fraud vs general)
- **Band-calibrated confidence (`γ_band`)** — epistemic-band correction (+0.15 low, −0.10 high)

### Security & Trust
- **Minimal DID integration** — `did:key` local resolution (no network), Ed25519 signature verification, `KeyRegistry` with YAML persistence and Git commit soft-checks
- **EventChain signature verification** — `verify_integrity(registry=KeyRegistry)` optionally validates Ed25519 signatures
- **Transparency anchor** — `TransparencyAnchor` class for deterministic chain-hash anchors in `ANCHOR.md`

### Semantic Web Interoperability
- **OWL 2 bidirectional** — `export_owl()` + `parse_owl_turtle()` / `parse_owl_rdfxml()` for round-trip Protégé interoperability
- **RDF-star / SPARQL-star** — `document_to_rdfstar_turtle()` and `sparqlstar_query_template()` for annotated triple provenance
- **JSON-LD export** — `export_jsonld()` for semantic-web APIs and graph databases

### Governance & Validation
- **L3 Relation Reconciliation** — `RelationValidator` enforcing Invariant 2: relations invalid when either endpoint is archived or both deprecated; fork inheritance rules
- **12-axiom well-formedness** — full `verify_integrity()` with distinct event_ids, timestamp monotonicity, payload schema, hash format, canonical fields, action preconditions, valid event_type checks
- **CRDT EventChain merge** — LWW-Set merge: union, deduplicate, sort, recompute hashes (Theorem 9)
- **Near-duplicate detection** — `check_near_duplicate()` with Jaccard/Levenshtein + optional sentence embeddings
- **Canon version** — `CANON_VERSION = "1.0"` in event hash for future algorithm change detection
- **N_min validator threshold** — `validator_count >= 1` precondition in ontology YAML (configurable `min_distinct_validators`)
- **Reproduce script** — `reproduce.sh` one-command reproduction (6 steps, 8–10 min, CI-friendly exit codes, `--quick` mode)

### Test & Experiment Coverage
- **723 tests** — all passing (446 unit + 11 experiment + 32 adversarial + 32 invalid-chain + 128 theorem + 23 theorem T1/T2/T6 + 6 boundary + 38 near-duplicate)
- **21 experiments** (E1–E21) — covering chain integrity, status derivation, snapshot round-trip, precondition enforcement, 5-agent audit, AML pipeline, real-time watcher, edge sync, git baseline, FDE pipeline, side-effect stress, and more

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

# Run tests (723 passed)
pytest tests/ -q
```

### CLI

```bash
# Validate
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md

# Parse
adl-lite parse examples/capital_reflux_trap.md

# Consensus (capability lifecycle)
adl-lite consensus register examples/capital_reflux_trap.md
adl-lite consensus transition disc-capital-trap --to validated --actor agent_1

# Ontology query
adl-lite ontology query --json
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
print(chain.confidence)       # O(1) — last VALIDATE event
print(chain.aggregated_confidence())  # Bonus-formula aggregate
print(chain.history())        # Full audit log

# Action execution
mgr = OntologyManager()
executor = ActionExecutor(mgr)
errors = executor.validate_action(doc, action_block)

# Data import (IBM AML stress test)
from adl_lite.data_importer import DataImporter
chains = DataImporter().import_csv("HI-Small_Trans.csv",
    event_type=EventType.REGISTER, concept_id_field="Account")

# Calibration (4 strategies)
print(chain.confidence)                  # O(1) — last VALIDATE
print(chain.aggregated_confidence())       # γ_agg — bonus-formula
print(chain.ewma_confidence(alpha=0.3))   # γ_ewma — time-decay
print(chain.band_calibrated_confidence())  # γ_band — epistemic correction

# DID signature verification
from adl_lite import KeyRegistry
registry = KeyRegistry()
chain.verify_integrity(registry=registry)  # Verify Ed25519 signatures

# OWL / JSON-LD / RDF-star export
from adl_lite import export_owl, export_jsonld, document_to_rdfstar_turtle
owl_ttl = export_owl(doc, format="turtle")
jsonld = export_jsonld(doc)
rdfstar = document_to_rdfstar_turtle(doc)

# L3 Relation validation
from adl_lite import RelationValidator
validator = RelationValidator()
valid = validator.valid(relation, source_status, target_status)

# Near-duplicate detection
from adl_lite import check_near_duplicate, suggest_merge
matches = check_near_duplicate(doc, existing_chains, threshold=0.85)
merge_suggestion = suggest_merge(doc, existing_chains)
```

## Project Structure

```
adl-lite/
├── adl_lite/              # Main package
│   ├── __init__.py        # Public API exports
│   ├── models.py          # Event, EventChain, ADLDocument, PreconditionRule
│   ├── parser.py          # L1/L2/L3/L4 parser
│   ├── validator.py       # SSA validation + scope ACL
│   ├── consensus.py       # Consensus chain + fork
│   ├── action_executor.py # Action execution + precondition checking
│   ├── data_importer.py   # CSV/JSON → Event import
│   ├── ontology.py        # OntologyManager (predicates/actions/transitions)
│   ├── memory.py          # Hot/Warm/Cold index
│   ├── tools.py           # Agent tool wrappers
│   ├── crdt.py            # CRDT merge semantics + LWW-Set EventChain merge
│   ├── calibration.py     # MARGINCalibrator + γ_agg / γ_cal
│   ├── owl_export.py      # OWL 2 DL export (RDF/XML + Turtle)
│   ├── jsonld_export.py   # JSON-LD export
│   ├── near_duplicate.py  # Near-duplicate detection
│   ├── realtime.py        # Real-time event watcher
│   ├── sync_manager.py    # Edge-to-core sync coordination
│   ├── did_resolver.py    # Minimal did:key resolution (local, no network)
│   ├── key_registry.py    # Key registry + transparency anchor + DID support
│   ├── relation_validator.py # L3 Relation Reconciliation (Invariant 2)
│   ├── owl_import.py      # OWL 2 DL import (Turtle + RDF/XML round-trip)
│   ├── rdfstar_export.py  # RDF-star / SPARQL-star export for annotated triples
│   ├── cold_storage.py    # Cold storage + archive
│   ├── cli.py             # adl-lite CLI entry point
│   └── adl_core_ontology.yaml # v0.2: classes + predicates + actions + collusion_resistance
├── experiments/
│   ├── base.py            # BaseExperiment + ExperimentResult
│   ├── registry.py        # @register("E1") decorator
│   ├── runner.py          # python -m experiments.runner all
│   ├── harness.py         # 5-agent simulation harness
│   └── e*.py              # 21 registered experiments
├── tests/                 # pytest suite (716 tests)
├── examples/              # Capability file examples
├── data/aml/              # AML domain stress test data
├── docs/
│   ├── paper_ao/          # Applied Ontology journal submission (39pp)
│   ├── paper_v3/          # ESWC/ISWC 2027 LNCS version
│   ├── proposals/         # Design proposals
│   └── *.md               # Operational docs (see AGENTS.md for current guide)
├── reproduce.sh           # One-command reproduction script
├── archive/               # Deprecated files
├── pyproject.toml         # Package config, ruff, mypy
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
| **$\gamma(C)$** | O(1) confidence from last VALIDATE event |
| **$\gamma_{agg}(C)$** | Bonus-formula aggregate: per-actor maxima + quorum bonuses |
| **$\gamma_{cal}(C)$** | Per-actor accuracy-weighted calibrated confidence |
| **$\gamma_{ewma}(C)$** | EWMA-calibrated confidence with time-decay (α configurable, default 0.3) |
| **$\gamma_{ctx}(C)$** | Per-domain context-calibrated confidence (e.g., AML vs fraud vs general) |
| **$\gamma_{band}(C)$** | Epistemic-band calibrated confidence (over/under-correction) |
| **Action Type** | L4 blocks: declarative actions + Comparator preconditions (no eval()) |
| **Trust Model** | Hash chain integrity + canonicalization version + Ed25519/DIDs (minimal did:key) |
| **Relation Validator** | Invariant 2: L3 relation validity based on endpoint lifecycle status |
| **RDF-star** | Embedded triple annotations for event provenance in triple stores |

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
| 🔄 Active | Paper revision | Major revision for Applied Ontology (39pp, 9 theorems) |
| 📋 Planned | Full DID suite | did:web, did:ethr, LD-Proofs, Merkle trees |
| 📋 Planned | Expert validation | AML/financial-crimes expert calibration |
| 📋 Planned | SHACL validation | Runtime shape validation |
| 📋 Planned | LLM discovery | Embedding-based canonicalisation |
| 📋 Planned | Machine-checked proofs | TLA⁺, Coq/Iris formal verification |
| 📋 Planned | Scale target | 1M events, 10K concurrent agents |

---

## License

MIT License — see [LICENSE](LICENSE)
