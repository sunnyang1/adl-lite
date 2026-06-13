# ADL Lite — An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AAMAS 2027 Target](https://img.shields.io/badge/Target-AAMAS%202027-blue.svg)](https://aamas2027.org/)
[![Applied Ontology: under revision](https://img.shields.io/badge/Journal-Applied%20Ontology-orange.svg)](https://www.iospress.nl/journal/applied-ontology/)
[![Tests: 410 PASS](https://img.shields.io/badge/tests-410%20PASS-brightgreen.svg)]()
[![Paper: 72pp](https://img.shields.io/badge/paper-72pp-blue.svg)]()

> **"The world is the totality of facts, not of things." — Wittgenstein, Tractatus Logico-Philosophicus §1.1**

ADL Lite is an **event-first, Markdown-native capability-lifecycle registry** for LLM agent ecosystems. Each capability (tool, API, knowledge domain) is represented as an **append-only, cryptographically hash-linked EventChain**. Status, confidence, and validators are **never stored as mutable fields** — all derived deterministically from the event history.

ADL Lite fills the gap between **KYA** (permissions layer) and **AgentSafe** (architecture-level governance): a lightweight, verifiable registry that records what agents can do, how capabilities evolve, and whether they remain trustworthy.

## Architecture

```
Markdown capability file (L1/L2/L3/L4)
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
| **paper_ao/** | Applied Ontology journal — under revision (72 pp, 40+ refs) |
| **Target venue** | AAMAS 2027 (backup: ESWC/ISWC 2027) |
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
| E6 | IBM AML pipeline (architectural stress test) | 201 chains, 9,300 events, 100% integrity |
| E13 | Long-chain stress | Linear to 50k events, $R^2 = 1.0$ |
| E14 | Collusion vulnerability | 1 actor → $\gamma = 0.99$ (Phase 1 limitation) |
| E15 | Precondition boundary | 4/11 caught by Pydantic (defense-in-depth gap) |
| E16 | Contention simulation | 95% rejection at $k=20$ (no fork-on-conflict) |

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

# Run tests (410 passed)
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
print(chain.history())        # Full audit log

# Action execution
mgr = OntologyManager()
executor = ActionExecutor(mgr)
errors = executor.validate_action(doc, action_block)

# Data import (IBM AML stress test)
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
│   └── e6_aml_pipeline.py     # IBM AML pipeline (architectural stress test)
├── docs/
│   ├── paper_ao/              # Applied Ontology journal submission (72pp)
│   │   ├── main.tex/PDF       # 7 sections + 6 appendices
│   │   ├── sections/          # 01_intro ... 07_conclusion + appendices A–F
│   │   └── references.bib     # 40+ references
│   ├── paper_v3/              # ESWC/ISWC 2027 LNCS version (11 experiments)
│   ├── REVIEW_RESPONSE_PLAN.md # AO reviewer revision plan
│   ├── SPEC.md                # Specification
│   └── proposals/             # Design proposals
├── archive/                   # Deprecated files
├── examples/                  # Capability file examples
├── tests/                     # pytest (410 tests)
├── data/aml/                  # AML domain stress test data
└── scripts/                   # Build / reproduce / CI scripts
```

## Core Concepts

| Term | Definition |
|------|-----------|
| **EventChain** | Append-only, cryptographically hash-linked event sequence. Capability = chain. |
| **Event** | Atomic event: event_type, actor, payload, hash, previous_event_id |
| **Event-first** | Status/confidence/validators derived from chain, no mutable fields stored |
| **Capability** | A claim an agent makes: "I can retrieve weather data", "I can execute SQL" |
| **$\delta(C)$** | Deterministic status derivation function |
| **$\gamma(C)$** | Confidence aggregation with per-validator maxima and quorum bonuses |
| **Action Type** | L4 blocks: declarative actions + Comparator preconditions (no eval()) |
| **Trust Model** | Hash chain integrity + planned Ed25519/DIDs (Phase 3) |

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

## License

MIT License — see [LICENSE](LICENSE)
