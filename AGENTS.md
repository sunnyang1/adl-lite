# ADL Lite — Agent Guide

Markdown-native **event-first operational ontology** for agentic KG authoring and multi-agent concept consensus (primary: Applied Ontology journal; backup: ESWC/ISWC 2027).

Philosophy: Wittgenstein Tractatus §1.1 — "The world is the totality of facts, not of things." → Action-first. Concepts are event chains.

## Project Overview

ADL Lite is a Python 3.10+ package that implements a four-layer document model for concept representation and multi-agent consensus. Every concept is an append-only, cryptographically hashed `EventChain`. Status, confidence, and validators are **derived from the chain**, never stored as mutable fields.

- **Version**: 0.2.0 (code-paper aligned, 590 tests)
- **License**: MIT
- **Build backend**: hatchling
- **Entry point**: `adl-lite` CLI (`adl_lite.cli:main`)

## Technology Stack

| Dependency | Minimum | Purpose |
|------------|---------|---------|
| Python | 3.10 | Runtime |
| pydantic | 2.0 | Data models & validation |
| pyyaml | 6.0 | YAML front-matter parsing |
| networkx | 3.0 | Graph operations (relations, memory) |
| pytest | 7.0 | Test runner (dev) |
| pytest-cov | 4.0 | Coverage (dev) |
| mypy | 1.0 | Static type checking (dev) |
| ruff | 0.1.0 | Linting & formatting (dev) |

Optional experiment dependencies:
- `openai>=1.0`, `anthropic>=0.25` (experiments)
- `sentence-transformers>=2.2` (experiments-embeddings, near-duplicate detection)

## Build, Install, and Test Commands

```bash
# Development install
pip install -e ".[dev]"

# Run all unit tests with coverage
pytest tests/ -v --cov=adl_lite --cov-report=xml --cov-report=term-missing

# Run all scripted experiments
python -m experiments.runner all

# List experiments
python -m experiments.runner list

# Run a single experiment
python -m experiments.runner E2 --verbose

# Lint (matches CI)
ruff check adl_lite/

# Type check (matches CI)
mypy adl_lite/ --ignore-missing-imports

# Pre-commit (runs ruff + mypy)
pre-commit run --all-files
```

## Code Style Guidelines

- **Line length**: 100 characters (`tool.ruff.line-length = 100`)
- **Target Python**: 3.10 (`target-version = "py310"`)
- **Excluded paths**: `archive/`, `data/aml/scripts/`
- **Lint rules**: E, F, W, I, N, UP, B, C4 (ruff select)
- **Ignored rules**: E501 (line too long — handled by formatter)
- **Format**: ruff-format (enforced in CI and pre-commit)
- **Type hints**: Encouraged but not mandatory (`disallow_untyped_defs = false` in mypy)
- **Docstrings**: Module-level docstrings explain architecture; classes explain design intent.
- **Comments**: Code comments and docstrings are in English. User-facing CLI output may be bilingual.

## Architecture

### Four-Layer Document Model

| Layer | Syntax | Role | Event Types |
|-------|--------|------|-------------|
| L1 | YAML front matter | Identity metadata (derived snapshot) | SNAPSHOT |
| L2 | Markdown body | Human/LLM prose, `[[Wiki Links]]` | — |
| L3 | `adl:*` fenced blocks | Semantic assertions (relation, evidence, seal) | RELATE, EVIDENCE, SEAL |
| L4 | `adl:action` fenced blocks | Typed actions with preconditions & side effects | REGISTER, VALIDATE, FORK, ... |

### Module Reference

| Module | Role |
|--------|------|
| `adl_lite/parser.py` | L1 YAML, L2 Markdown body, L3 `adl:*` blocks, L4 `adl:action` blocks |
| `adl_lite/models.py` | Pydantic types: `Event`, `EventChain`, `ADLDocument`, L3/L4 blocks, `PreconditionRule` |
| `adl_lite/validator.py` | SSA semantic validation + scope ACL |
| `adl_lite/consensus.py` | Status transitions, forks, chain integrity |
| `adl_lite/action_executor.py` | Action validation (preconditions) + side-effect dispatch |
| `adl_lite/data_importer.py` | CSV/JSON → Event import + ontology discovery |
| `adl_lite/ontology.py` | `OntologyManager` — predicates, actions, transitions from YAML registry |
| `adl_lite/memory.py` | Hot/Warm/Cold hybrid index (`ADLMemory`) |
| `adl_lite/tools.py` | Agent-facing Python wrappers matching CLI semantics |
| `adl_lite/calibration.py` | `MARGINCalibrator` + `aggregated_confidence()` + `calibrated_confidence()` |
| `adl_lite/crdt.py` | CRDT merge semantics + `merge_event_chains()` (LWW-Set, Theorem 9) |
| `adl_lite/owl_export.py` | OWL 2 DL export (RDF/XML + Turtle) |
| `adl_lite/jsonld_export.py` | JSON-LD export for semantic-web APIs |
| `adl_lite/near_duplicate.py` | Near-duplicate detection (Jaccard / Levenshtein / embeddings) |
| `adl_lite/realtime.py` | Real-time event watcher and stream ingestion |
| `adl_lite/sync_manager.py` | Edge-to-core sync coordination |
| `adl_lite/l2_template.py` | L2 template schema + validation |
| `adl_lite/key_registry.py` | Key registry + transparency anchor |
| `adl_lite/cold_storage.py` | Cold storage + archive |
| `experiments/base.py` | `BaseExperiment` + `ExperimentResult` |
| `experiments/registry.py` | `@register("E1")` decorator for experiment discovery |
| `experiments/runner.py` | `python -m experiments.runner` CLI |
| `experiments/harness.py` | Scripted 5-agent simulation harness |

Public API:
```python
from adl_lite import (
    parse_file, parse_text, ADLParser, ADLParseError,
    Event, EventChain, EventType, DiscoveryStatus,
    ADLDocument, ADLFrontMatter, ADLActionBlock, ADLRelationBlock, ADLEvidenceBlock,
    Comparator, PreconditionRule, ActionDef, ActionExecStatus,
    ConceptSkeleton, ExecutionEntry,
    ADLValidator, OntologyManager, ActionExecutor,
    ConsensusEngine, ForkManager, ForkResolution,
    ADLMemory, HotIndex, WarmIndex,
    # New in code-paper alignment
    CalibrationProfile, MARGINCalibrator, aggregated_confidence, calibrated_confidence,
    CRDTState, StatusOrder, merge_event_chains,
    export_owl, export_jsonld,
    check_near_duplicate, suggest_merge,
)
```

### Event-First Design

```python
from adl_lite import Event, EventChain, EventType, DiscoveryStatus

# Concept = EventChain (not a mutable object)
chain = EventChain(concept_id="disc-capital-trap")

chain.append(Event(concept_id="disc-capital-trap",
                   event_type=EventType.REGISTER, actor="discoverer"))
chain.append(Event(concept_id="disc-capital-trap",
                   event_type=EventType.VALIDATE, actor="reviewer",
                   payload={"confidence": 0.85}))

# Status is derived from chain, NOT stored
assert chain.status == DiscoveryStatus.VALIDATED
assert chain.confidence == 0.85
assert chain.verify_integrity()
assert len(chain.history()) == 2
```

## CLI Commands

```bash
# Parse & validate
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md
adl-lite parse examples/capital_reflux_trap.md

# Memory
adl-lite store examples/capital_reflux_trap.md --db /tmp/adl.db
adl-lite related concept-gradient-explosion --db /tmp/adl.db

# Consensus
adl-lite consensus register examples/capital_reflux_trap.md
adl-lite consensus transition disc-capital-trap --to validated --actor agent_1
adl-lite consensus verify disc-capital-trap

# Ontology
adl-lite ontology validate
adl-lite ontology validate --examples --aml
adl-lite ontology query --json
adl-lite ontology query --predicate isomorphic-to
```

## Agent Tools (Python)

```python
from adl_lite.tools import adl_parse, adl_validate, adl_store, adl_query_related
from adl_lite.tools import adl_consensus_register, adl_consensus_transition, adl_ontology_query
from adl_lite.action_executor import ActionExecutor
from adl_lite.ontology import OntologyManager

# Action validation
mgr = OntologyManager()
executor = ActionExecutor(mgr)
errors = executor.validate_action(doc, action_block)

# Event chain
chain = doc.event_chain
chain.verify_integrity()
chain.history()

# Data import
from adl_lite.data_importer import DataImporter
chains = DataImporter().import_csv("data.csv", event_type=EventType.REGISTER, concept_id_field="id")

# OWL / JSON-LD export
from adl_lite import export_owl, export_jsonld
owl_ttl = export_owl(doc, format="turtle")
jsonld = export_jsonld(doc)

# Near-duplicate detection
from adl_lite import check_near_duplicate, suggest_merge
matches = check_near_duplicate(doc, existing_chains, threshold=0.85)
merge_suggestion = suggest_merge(doc, existing_chains)
```

## ADL Document Shape (L1/L2/L3/L4)

- **L1**: YAML with `adl_type`, `adl_id`, `status`, `confidence`, `scope`, etc.
- **L2**: Markdown body (human/LLM prose, `[[Wiki Links]]`)
- **L3**: Fenced blocks: `adl:relation`, `adl:evidence`, `adl:seal`
- **L4**: Fenced blocks: `adl:action` with `action`, `actor`, `reasoning`, `params`

```markdown
```adl:action
action: validate
actor: agent_3
reasoning: "Cross-domain validation complete"

params:
  confidence_boost: 0.15
```
```

## Ontology Registry (`adl_core_ontology.yaml` v0.2)

Closed sets:
- **classes**: `discovery`, `concept`, `relation`, `evidence`, `formal_seal`
- **predicates**: `isomorphic-to`, `specialisation-of`, `co-occurs-with`, `related-to`, `analogical-to`, `analogical-transfer`, `dual-of`, `fork-of`, `mitigated-by`, `indexed-phrase`
- **actions**: `register`, `validate`, `fork`, `deprecate`, `archive`, `announce`, `publish`, `sync_dashboard`, `listen`
- **status_transitions**: `provisional` → `validated`/`deprecated`/`forked`/`archived`, `validated` → `deprecated`/`forked`/`archived`, ...
- **collusion_resistance**: `min_distinct_validators: 1` (configurable)

## Testing Strategy

- **Framework**: pytest with `pytest-cov`
- **Test count**: ~45 test files under `tests/`, 590 tests total
- **Coverage target**: Run with `--cov=adl_lite --cov-report=term-missing`
- **Fixtures**: Shared fixtures in `tests/fixtures/` and `tests/conftest.py`
- **Experiment tests**: `tests/test_experiments.py` validates experiment infrastructure
- **Theorem tests**: `tests/test_theorems.py` covers T4, T5, T7, T8, T9
- **Before claiming work complete**, run:
  ```bash
  pytest tests/ -v
  python -m experiments.runner all
  ```

## Experiments (13+ registered)

```bash
python -m experiments.runner all
```

| ID | Name | Module Under Test |
|----|------|-------------------|
| E1 | Chain integrity | EventChain |
| E2 | Status derivation | EventChain |
| E3 | Snapshot roundtrip | EventChain + FrontMatter |
| E4 | Precondition enforcement | ActionExecutor |
| E5 | 5-agent audit | ConsensusEngine + harness |
| E6 | IBM AML pipeline | DataImporter + EventChain + patterns |
| E7 | Real-time watcher | realtime.py |
| E8 | Edge sync | sync_manager.py |
| E9 | Git baseline | parser + consensus |
| E10 | FDE pipeline | OntologyManager + ActionExecutor |
| E11 | Side-effect stress | ActionExecutor + side effects |
| E13 | Long-chain stress | EventChain |
| E14 | Collusion vulnerability | Calibration |
| E16 | Contention simulation | ConsensusEngine |
| E20 | Template effectiveness | L2Template |
| E20b | Calibration baseline | Calibration |
| E21 | 100k event stress | EventChain + cold storage |
| E23 | Contention stress | SyncManager + concurrent agents |

## CI / CD Pipeline

GitHub Actions (`.github/workflows/ci.yml`):

1. **Lint** (`ruff check adl_lite/`)
2. **Test matrix** (Python 3.10, 3.11, 3.12) with coverage → Codecov
3. **Type check** (`mypy adl_lite/ --ignore-missing-imports`)

Pre-commit hooks (`.pre-commit-config.yaml`):
- `ruff` (lint + auto-fix)
- `ruff-format`
- `mypy` (with `pydantic>=2.0`, `types-PyYAML`)

## Conventions & Design Rules

- **Event-first**: `status`/`confidence`/`validators` are derived from `EventChain`, NOT stored.
- **Status flow**: `provisional` → `validated` / `deprecated` / `forked` / `archived`
- **Scopes**: `public`, `private/<org>`, `user/<id>`, `shared/<collab>`
- **Precondition rules**: `Comparator` enum (`EQ`/`NEQ`/`GT`/`GTE`/`LT`/`LTE`/`IN`/`EXISTS`). **NO `eval()`**.
- **Cryptographic chaining**: Each `Event` stores a SHA-256 hash that includes its predecessor's hash and `canon_version`. `EventChain.verify_integrity()` validates the full chain (12 axioms).
- **Thread safety**: `EventChain` uses `threading.Lock` around mutations and reads.
- **Synthetic events**: Events reconstructed from YAML front matter during parsing are tagged `synthetic=True` in their payload to distinguish them from agent-authored actions.
- **Front matter is a snapshot**: `ADLFrontMatter` is a derived view of the chain, not the source of truth. Mutate the chain, then call `refresh_snapshot()`.
- **Confidence boundedness**: `chain.confidence` clamps to [0,1] (Theorem 4). `chain.aggregated_confidence()` returns bonus-formula aggregate. `chain.calibrated_confidence()` returns accuracy-weighted calibrated confidence.
- **Well-formedness**: `verify_integrity()` checks 12 axioms (Definition 5 in paper §4.6).

## Security Considerations

- **No `eval()` or `exec()`**: Precondition evaluation uses a closed `Comparator` enum with explicit operator dispatch. Never use dynamic evaluation on user input.
- **Hash integrity**: Event hashes include the previous event's hash and `canon_version`, forming a tamper-evident chain. Any modification breaks `verify_integrity()`.
- **Scope ACL**: `ADLValidator` enforces scope prefix rules (`public`, `private/`, `user/`, `shared/`).
- **CSV/JSON import**: `DataImporter` reads tabular data and maps rows to events. Validate `concept_id_field` and payload shapes before appending to chains in production scenarios.
- **Collusion resistance**: `validate` action requires `validator_count >= N_min` (default 1, configurable via ontology YAML). The bonus-formula `γ_agg` and accuracy-weighted `γ_cal` both mitigate collusion by low-accuracy validators.

## Project Structure Summary

```
adl-lite/
├── adl_lite/              # Main package
│   ├── adl_core_ontology.yaml
│   ├── __init__.py
│   ├── action_executor.py
│   ├── calibration.py
│   ├── cli.py
│   ├── consensus.py
│   ├── crdt.py
│   ├── cold_storage.py
│   ├── data_importer.py
│   ├── jsonld_export.py
│   ├── key_registry.py
│   ├── l2_template.py
│   ├── memory.py
│   ├── models.py
│   ├── near_duplicate.py
│   ├── ontology.py
│   ├── owl_export.py
│   ├── parser.py
│   ├── realtime.py
│   ├── sync_manager.py
│   ├── tools.py
│   └── validator.py
├── tests/                 # pytest suite (590 tests)
├── experiments/           # 13+ scripted experiments
├── examples/              # Sample ADL Markdown files
├── data/aml/              # AML dataset + concepts
├── docs/                  # Paper, specs, proposals, reports
├── archive/               # Deprecated files (excluded from lint)
├── pyproject.toml         # Package config, ruff, mypy
├── .github/workflows/ci.yml
└── .pre-commit-config.yaml
```
