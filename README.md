# ADL Lite — Event-First Operational Ontology

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ESWC + ISWC 2027 Target](https://img.shields.io/badge/Target-ESWC%20%2B%20ISWC%202027-blue.svg)](https://eswc-conferences.org/)
[![Applied Ontology: under revision](https://img.shields.io/badge/Journal-Applied%20Ontology-orange.svg)](https://www.iospress.nl/journal/applied-ontology/)
[![Tests: 387 PASS](https://img.shields.io/badge/tests-387%20PASS-brightgreen.svg)]()
[![Paper: 52pp, 30 refs](https://img.shields.io/badge/paper-52pp%2C%2030%20refs-blue.svg)]()

> **"The world is the totality of facts, not of things." — Wittgenstein, Tractatus Logico-Philosophicus §1.1**

ADL Lite is an **event-first, Markdown-native operational ontology** for concept lifecycle governance in multi-agent and LLM-intensive settings. Each concept is an **append-only, cryptographically hash-linked EventChain**. Status, confidence, and validators are **never stored as mutable fields** — all derived deterministically from the event history.

Referencing Palantir Foundry Data Engine's ontology layer (Object Type / Property Type / Link Type / Action Type), but implemented as Markdown-native, Git-backed, pip-installable toolkit.

## Architecture

```
Markdown concept file (L1/L2/L3/L4)
        ↓
ADLParser → ADLDocument + EventChain
        ↓
OntologyManager ← adl_core_ontology.yaml (classes / predicates / actions)
        ↓
ActionExecutor (precondition validation + side effects)
        ↓
ConsensusEngine (append-only transition chain)
        ↓
ADLMemory (Hot skeleton / Warm SQLite+NetworkX / Cold archive)
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
from adl_lite import Event, EventChain, EventType

chain = EventChain(concept_id="disc-capital-trap")

chain.append(Event(concept_id="disc-capital-trap",
                   event_type=EventType.REGISTER,
                   actor="discoverer"))

chain.append(Event(concept_id="disc-capital-trap",
                   event_type=EventType.VALIDATE,
                   actor="reviewer",
                   payload={"confidence": 0.85}))

# Status derived from chain, NOT stored
assert chain.status == DiscoveryStatus.VALIDATED
assert chain.confidence == 0.85
assert chain.verify_integrity()  # SHA-256 hash verification
```

## Paper Status

| Item | Status |
|------|--------|
| **paper_ao/** | Applied Ontology journal — under revision (52 pp, 30 refs, 0 placeholders) |
| **paper_v3/** | ESWC/ISWC 2027 LNCS format — 11 experiments, 3 appendices |
| Reviewer feedback | Addressed (P0+P1+P2, 12 items, 2026-06-03) |
| Revision plan | [`docs/REVIEW_RESPONSE_PLAN.md`](docs/REVIEW_RESPONSE_PLAN.md) |

**Key properties (formaised in paper_ao Section 4.6):**

| Theorem | Property |
|---------|----------|
| T1 | Determinism of $\delta(C)$ |
| T2 | Confluence under fork |
| T3 | Status transition monotonicity |
| T4 | Confidence boundedness $\gamma(C) \in [0,1]$ |
| T5 | Confidence monotonicity under independent validation |
| T6 | Status–confidence consistency ($\delta = $ validated $\implies \gamma \geq 0.5$) |
| T7 | CRDT convergence under LWW-Set merge |
| Corollary | Event-level G-Set CRDT |

## Experiments

**paper_ao** (6 experiments, foundational correctness):
| # | Experiment | Key Metric |
|---|-----------|-----------|
| E1 | Chain integrity | 60 chains: P=R=F1=1.0 |
| E2 | Status derivation | 2,204 cases: 100% correct |
| E4 | Precondition enforcement | 13 cases: P=R=F1=1.0 |
| E6 | IBM AML pipeline | 201 chains, 9,300 events, 100% integrity |

**paper_v3** (11 experiments, extended scale):
E1–E6 + E7 (Realtime pattern detection), E8 (Edge offline sync), E9 (Git-only baseline), E10 (Full FDE pipeline), E11 (Side-effect stress test)

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

# Run tests (387 passed)
pytest tests/ -q
```

### CLI

```bash
# Validate
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md

# Parse
adl-lite parse examples/capital_reflux_trap.md

# Consensus
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
print(chain.history())        # Full audit log

# Action execution
mgr = OntologyManager()
executor = ActionExecutor(mgr)
errors = executor.validate_action(doc, action_block)

# Data import (IBM AML)
from adl_lite.data_importer import DataImporter
chains = DataImporter().import_csv("HI-Small_Trans.csv",
    event_type=EventType.REGISTER, concept_id_field="Account")
```

## Project Structure

```
adl-lite/
├── adl_lite/
│   ├── models.py              # Event, EventChain, ADLActionBlock, PreconditionRule
│   ├── parser.py              # L1/L2/L3/L4 parser
│   ├── validator.py           # SSA validation + scope ACL
│   ├── consensus.py           # Consensus chain + fork
│   ├── action_executor.py     # Action execution + precondition checking
│   ├── data_importer.py       # CSV/JSON → Event import
│   ├── ontology.py            # OntologyManager (predicates/actions/transitions)
│   ├── memory.py              # Hot/Warm/Cold index
│   ├── tools.py               # Agent tool wrappers
│   ├── crdt.py                # CRDT merge semantics
│   ├── lark/                  # Feishu bridge
│   └── adl_core_ontology.yaml # v0.2: classes + predicates + actions
├── experiments/
│   ├── base.py                # BaseExperiment + ExperimentResult
│   ├── registry.py            # @register("E1") decorator
│   ├── runner.py              # python -m experiments.runner all
│   ├── harness.py             # 5-agent simulation harness
│   ├── e1_chain_integrity.py  # Chain integrity
│   ├── e2_status_derivation.py # Status derivation
│   ├── e3_snapshot_roundtrip.py # Snapshot round-trip
│   ├── e4_precondition.py     # Precondition enforcement
│   ├── e5_agent_audit.py      # Multi-agent audit
│   └── e6_aml_pipeline.py     # IBM AML pipeline
├── docs/
│   ├── paper_ao/              # Applied Ontology journal submission (52pp)
│   │   ├── main.tex/PDF       # 7 sections + 6 appendices
│   │   ├── sections/          # 01_intro ... 07_conclusion + appendices A–F
│   │   └── references.bib     # 30 real references
│   ├── paper_v3/              # ESWC/ISWC 2027 LNCS version (11 experiments)
│   ├── REVIEW_RESPONSE_PLAN.md # AO reviewer revision plan (2026-06-03)
│   ├── SPEC.md                # Specification
│   └── proposals/             # Design proposals
├── archive/                   # Deprecated files
├── examples/                  # Concept file examples
├── tests/                     # pytest (387 tests)
├── data/aml/                  # AML concepts + queries
└── scripts/                   # Build / reproduce / CI scripts
```

## Core Concepts

| Term | Definition |
|------|-----------|
| **EventChain** | Append-only, cryptographically hash-linked event sequence. Concept = chain. |
| **Event** | Atomic event: event_type, actor, payload, hash, previous_event_id |
| **Event-first** | Status/confidence/validators derived from chain, no mutable fields stored |
| **$\delta(C)$** | Deterministic status derivation function |
| **$\gamma(C)$** | Confidence aggregation with per-validator maxima and quorum bonuses |
| **Action Type** | L4 blocks: declarative actions + Comparator preconditions (no eval()) |
| **Trust Model** | Hash chain integrity + planned Ed25519/DIDs (Phase 3) |

## Consensus States

| provisional | validated | deprecated | forked | archived |
|:---:|:---:|:---:|:---:|:---:|

## License

MIT License — see [LICENSE](LICENSE)
