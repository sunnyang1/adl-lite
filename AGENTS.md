# ADL Lite — Agent Guide

Markdown-native **event-first operational ontology** for agentic KG authoring and multi-agent concept consensus (primary: Applied Ontology journal; backup: ESWC/ISWC 2027).

Philosophy: Wittgenstein Tractatus §1.1 — "The world is the totality of facts, not of things." → Action-first. Capabilities exist only as participants in events.

## Project Overview

ADL Lite is a Python 3.10+ package that implements a four-layer document model for capability representation and multi-agent consensus. Every concept/capability is an append-only, cryptographically hashed `EventChain`. Status, confidence, validators, and scope are **derived from the chain**, never stored as mutable fields.

- **Name**: `adl-lite`
- **Version**: `0.5.0-alpha` (per `CHANGELOG.md`; `pyproject.toml` updated on release)
- **Description**: ADL Lite — An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems
- **License**: MIT
- **Build backend**: hatchling
- **CLI entry point**: `adl-lite` (`adl_lite.cli:main`)
- **Homepage**: https://github.com/sunnyang1/adl-lite

## Technology Stack

| Dependency | Minimum | Purpose |
|------------|---------|---------|
| Python | 3.10 | Runtime |
| pydantic | 2.0 | Data models & validation |
| pyyaml | 6.0 | YAML front-matter / ontology registry |
| networkx | 3.0 | Graph operations (relations, memory) |
| fastapi | 0.109.0 | Web framework (FDE platform) |
| uvicorn[standard] | 0.27.0 | ASGI server (FDE platform) |
| sqlalchemy[asyncio] | 2.0.25 | Database ORM (FDE platform) |
| alembic | 1.13.0 | DB migrations (FDE platform) |
| aiosqlite | 0.19.0 | Async SQLite (FDE platform) |
| python-jose[cryptography] | 3.3.0 | JWT / auth (FDE platform) |
| cryptography | 41.0 | Crypto primitives |
| passlib[bcrypt] | 1.7.4 | Password hashing (FDE platform) |
| python-multipart | 0.0.6 | Form/multipart parsing |
| httpx | 0.26.0 | HTTP client |
| pydantic-settings | 2.1.0 | Settings / config |
| apscheduler | 3.10.4 | Task scheduling |
| openai | 1.0 | LLM client |
| anthropic | 0.25 | LLM client |
| websockets | 12.0 | WebSocket support |

Development extras (`pip install -e ".[dev]"`):
- `pytest>=7.0`, `pytest-cov>=4.0`, `pytest-asyncio>=0.23.0`, `pytest-benchmark>=4.0`, `mypy>=1.0`, `ruff>=0.1.0`, `rdflib>=7.0`, `pyshacl>=0.25`

Optional extras:
- `pip install -e ".[experiments]"` — LLM clients for experiment scripts
- `pip install -e ".[experiments-embeddings]"` — `sentence-transformers>=2.2` for near-duplicate detection
- `pip install -e ".[embeddings]"` — `sentence-transformers>=2.2`, `faiss-cpu>=1.7`, `openai>=1.0` (vector index + LLM normalization)
- `pip install -e ".[scale]"` — `faiss-cpu>=1.7`, `zstandard>=0.22`, `msgpack>=1.0` (large-scale cold storage)
- `pip install -e ".[prod]"` — PostgreSQL drivers (`psycopg[binary]>=3.1.0`, `asyncpg>=0.29.0`)
- `pip install -e ".[v1]"` — `redis>=5.0`, `celery>=5.3`

**Known dependency gap**: `experiments/e19_governance_benchmark.py` imports `pygit2`, which is **not** declared in `pyproject.toml`. `python -m experiments.runner list|all` fails unless you install `pygit2` manually in your environment.

## Build, Install, and Test Commands

```bash
# Development install
pip install -e ".[dev]"

# Run the full pytest suite
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=adl_lite --cov-report=xml --cov-report=term-missing

# Lint (matches CI)
ruff check adl_lite/

# Type check (matches CI)
mypy adl_lite/ --ignore-missing-imports

# Pre-commit (runs ruff + mypy)
pre-commit run --all-files

# List experiments (requires pygit2 to be installed)
python -m experiments.runner list

# Run a single experiment
python -m experiments.runner E2 --verbose

# Run all scripted experiments
python -m experiments.runner all

# One-command reproduction script
./reproduce.sh              # all core experiments
./reproduce.sh quick        # E1–E4 + E24 only
./reproduce.sh docker       # build & run Docker image
./reproduce.sh test         # pytest suite only

# Throughput benchmark used by CI
python experiments/benchmarks/throughput.py

# Paper–code consistency check
python scripts/consistency_check.py
```

## Code Style Guidelines

- **Line length**: 100 characters (`tool.ruff.line-length = 100`)
- **Target Python**: 3.10 (`target-version = "py310"`)
- **Excluded paths**: `archive/`, `data/aml/scripts/`
- **Lint rules**: E, F, W, I, N, UP, B, C4
- **Ignored rules**: `E501` (line too long — handled by formatter), `N999` (invalid module name)
- **Format**: ruff-format (enforced in CI and pre-commit)
- **Type hints**: Encouraged but not mandatory (`disallow_untyped_defs = false` in mypy)
- **Docstrings**: Module-level docstrings explain architecture; classes explain design intent. Use English for code comments and docstrings. User-facing CLI output may be bilingual.
- **File naming**: test files match `test_<module>.py`.

## Architecture

### Four-Layer Document Model

| Layer | Syntax | Role | Event Types |
|-------|--------|------|-------------|
| L1 | YAML front matter | Identity metadata (derived snapshot) | `SNAPSHOT` |
| L2 | Markdown body | Human/LLM prose, `[[Wiki Links]]` | — |
| L3 | `adl:*` fenced blocks | Semantic assertions (relation, evidence, seal) | `RELATE`, `EVIDENCE`, `SEAL` |
| L4 | `adl:action` fenced blocks | Typed actions with preconditions & side effects | `REGISTER`, `VALIDATE`, `FORK`, `DEPRECATE`, `ARCHIVE`, ... |

**Critical rule**: L1 front matter is a **derived snapshot**, not the source of truth. Mutate the chain via `EventChain.append()`, then call `doc.refresh_snapshot()` to update the derived view.

### Module Reference

| Module | Role |
|--------|------|
| `adl_lite/parser.py` | L1 YAML, L2 Markdown body, L3 `adl:*` blocks, L4 `adl:action` blocks |
| `adl_lite/models.py` | Pydantic types: `Event`, `EventChain`, `ADLDocument`, L3/L4 blocks, `PreconditionRule` |
| `adl_lite/validator.py` | SSA semantic validation + scope ACL + runtime SHACL (opt-in) + relation governance |
| `adl_lite/consensus.py` | Status transitions, forks, chain integrity, dynamic N_min enforcement |
| `adl_lite/action_executor.py` | Action validation (preconditions) + side-effect dispatch + calibration side effect |
| `adl_lite/data_importer.py` | CSV/JSON → Event import + ontology discovery |
| `adl_lite/ontology.py` | `OntologyManager` — predicates, actions, transitions from YAML registry |
| `adl_lite/memory.py` | Hot/Warm/Cold hybrid index (`ADLMemory`) with auto-archival |
| `adl_lite/cold_storage.py` | JSONL and zstd+msgpack cold storage for `EventChain` |
| `adl_lite/tools.py` | Agent-facing Python wrappers matching CLI semantics |
| `adl_lite/calibration.py` | `MARGINCalibrator` + `aggregated_confidence()` + `calibrated_confidence()` + EWMA / feedback calibration |
| `adl_lite/shacl_validation.py` | Runtime SHACL validation over PROV-O / ADLDocument |
| `adl_lite/crdt.py` | CRDT merge semantics + `merge_event_chains()` |
| `adl_lite/owl_export.py` | OWL 2 DL export (RDF/XML + Turtle) |
| `adl_lite/owl_import.py` | OWL 2 DL import (Turtle + RDF/XML round-trip) |
| `adl_lite/jsonld_export.py` | JSON-LD export for semantic-web APIs |
| `adl_lite/rdfstar_export.py` | RDF-star / SPARQL-star export |
| `adl_lite/embeddings.py` | Pluggable embedding backends (`SentenceTransformerBackend`, `OpenAIBackend`) |
| `adl_lite/vector_index.py` | FAISS-backed persisted vector index + semantic search |
| `adl_lite/near_duplicate.py` | Near-duplicate detection (Jaccard / Levenshtein / embeddings) |
| `adl_lite/canonicalization.py` | LLM-driven normalization: cluster → propose → emit ADL actions |
| `adl_lite/realtime.py` | Real-time event watcher and stream ingestion |
| `adl_lite/sync_manager.py` | Edge-to-core sync coordination |
| `adl_lite/l2_template.py` | L2 template schema + validation |
| `adl_lite/key_registry.py` | Ed25519 keys, Git signatures, Merkle transparency anchors |
| `adl_lite/did_resolver.py` | `DIDResolver` — `did:key`, `did:web`, `did:ethr` |
| `adl_lite/ld_proof.py` | W3C Linked Data Proofs (`Ed25519Signature2020`, `EcdsaSecp256k1Signature2019`) |
| `adl_lite/merkle.py` | SHA-256 Merkle trees with inclusion proofs for batch verification |
| `adl_lite/relation_validator.py` | L3 relation integrity (Invariant 2) |
| `adl_lite/cold_storage.py` | JSONL cold storage + archive |
| `adl_lite/fde/` | MVP Formal Data Engineering platform (pipeline, importer, tenant, rule engine) |
| `experiments/base.py` | `BaseExperiment` + `ExperimentResult` |
| `experiments/registry.py` | `@register("E1")` decorator for experiment discovery |
| `experiments/runner.py` | `python -m experiments.runner` CLI |
| `experiments/harness.py` | Scripted 5-agent simulation harness |
| `specs/EventChain.tla` | TLA+ bounded spec for single EventChain invariants (T1/T2/T3/T4/T5/T7) |
| `specs/CRDTMerge.tla` | TLA+ bounded spec for two-branch CRDT merge (T9) |
| `specs/ConsensusEngine.tla` | TLA+ bounded spec for multi-agent consensus with `N_min` validators |
| `scripts/run_tlc.py` | CLI wrapper that generates `MC.cfg` and invokes TLC |
| `formal/coq/` | Buildable Coq/Iris skeleton for unbounded proofs (T3/T4/T7/T9) |

### Public API

```python
from adl_lite import (
    parse_file, parse_text, ADLParser, ADLParseError, extract_wiki_links,
    Event, EventChain, EventType, DiscoveryStatus,
    ADLDocument, ADLFrontMatter, ADLActionBlock, ADLRelationBlock, ADLEvidenceBlock,
    ADLType, EvidenceType, MechanismType,
    Comparator, PreconditionRule, ActionDef, ActionExecStatus,
    ConceptSkeleton, ExecutionEntry,
    ADLValidator, OntologyManager, ActionExecutor,
    ConsensusEngine, ForkManager, ForkResolution,
    ADLMemory, HotIndex, WarmIndex,
    CalibrationProfile, MARGINCalibrator, aggregated_confidence, calibrated_confidence,
    CRDTState, StatusOrder, merge_event_chains,
    validate_adl_document,

    KeyRegistry, GitSignatureVerifier, TransparencyAnchor,
    DIDDocument, DIDResolver, VerificationMethod,
    create_did_key, resolve_did, resolve_did_key, resolve_did_web,
    verify_did_signature, is_did,
    create_event_proof, sign_event, verify_event_proof,
    MerkleProof, MerkleTree, compute_chain_merkle_root,
    export_owl, export_jsonld,
    parse_owl_turtle, parse_owl_rdfxml,
    document_to_rdfstar_turtle, sparqlstar_query_template,
    check_near_duplicate, check_near_duplicate_embedding, suggest_merge,
    EmbeddingBackend, SentenceTransformerBackend, OpenAIBackend,
    VectorIndex,
    CanonicalizationEngine, LLMBackend, OpenAILLMBackend,
    L2Template, L2TemplateValidator, RelationValidator,
    ADLError, ADLParseError, ADLValidationError, ADLOntologyError,
    ADLConsensusError, ADLMemoryError, ADLConfigError, ADLTemplateError,
    get_logger,
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

# Status, confidence, and validators are derived from the chain
assert chain.status == DiscoveryStatus.VALIDATED
assert chain.confidence == 0.85
assert chain.verify_integrity()
assert len(chain.history()) == 2
```

### CRDT Semantics

- **Status lattice** (`StatusOrder`): `provisional < forked < validated < deprecated < archived`
- `chain.status` derives via **Least Upper Bound (LUB)** over the lifecycle lattice; status never regresses.
- `chain.confidence` derives via **G-Counter (max)** over `VALIDATE` / `SNAPSHOT` events; lower confidence cannot downgrade an existing higher value.
- `merge_event_chains()` is commutative, associative, idempotent, and monotonic (LWW-Set by `event_id`, then timestamp sort and re-anchored hashes).

## CLI Commands

```bash
# Parse & validate
adl-lite parse examples/capital_reflux_trap.md
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md
adl-lite validate --strict-template examples/*.md

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
adl-lite ontology query --from-status provisional --to-status validated

# Normalization (vector + LLM; dry-run by default)
adl-lite normalize --input-dir ./concepts --threshold 0.92 --dry-run
adl-lite normalize --input-dir ./concepts --threshold 0.92 --execute

# Transparency anchor
adl-lite anchor
adl-lite anchor --merkle --proofs-dir ./proofs
adl-lite verify-anchor
adl-lite verify-inclusion <adl_id> --proof ./proofs/<adl_id>.json
```

## Agent Tools (Python)

```python
from adl_lite.tools import (
    adl_parse, adl_validate, adl_store, adl_query_related,
    adl_consensus_register, adl_consensus_transition, adl_consensus_verify,
    adl_ontology_query,
)
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
chains = DataImporter().import_csv("data.csv",
                                   event_type=EventType.REGISTER,
                                   concept_id_field="id")

# OWL / JSON-LD / RDF-star export
from adl_lite import export_owl, export_jsonld, document_to_rdfstar_turtle
owl_ttl = export_owl(doc, format="turtle")
jsonld = export_jsonld(doc)

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
```

## ADL Document Shape (L1/L2/L3/L4)

- **L1**: YAML with `adl_type`, `adl_id`, `status`, `confidence`, `scope`, `validators`, `provisional_names`, etc.
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
- **actions**: `register`, `validate`, `fork`, `deprecate`, `archive`, `announce`, `publish`, `sync_dashboard`, `listen`, `relate`, `evidence`, `seal`, `revoke`, `calibrate`
- **status_transitions**:
  - `provisional` → `validated` / `deprecated` / `forked` / `archived`
  - `validated` → `deprecated` / `forked` / `archived`
  - `forked` → `validated` / `deprecated` / `archived`
  - `deprecated` → `archived`
  - `archived` → []
- **scopes**: `public`, `private/<org>`, `user/<id>`, `shared/<collab>`
- **collusion_resistance**: `min_distinct_validators: 1` (read dynamically by `OntologyManager.min_distinct_validators()`; paper recommends `≥ 2` for production)

## Testing Strategy

- **Framework**: pytest with `pytest-cov`, `pytest-asyncio`, `pytest-benchmark`
- **Test files**: ~65 Python files under `tests/`
- **Test count**: 944 passed + 1 skipped in the current Python 3.12 environment
- **Fixtures**: Minimal shared fixtures in `tests/conftest.py` (path setup only); 3 Markdown fixtures in `tests/fixtures/`
- **FDE fixtures**: `tests/conftest_fde.py.bak` exists but is **not** auto-loaded by pytest, keeping the main suite lightweight
- **Theorem tests**:
  - `tests/test_theorem_t1.py`, `tests/test_theorem_t2.py`, `tests/test_theorem_t6.py`
  - `tests/test_theorems.py` covers T4, T5, T7, T8, T9
  - `tests/test_run_tlc.py` covers TLC runner config generation and argument parsing for the TLA+ specs
- **Experiment tests**: `tests/test_experiments.py` validates experiment infrastructure; `tests/test_E20b.py`, `tests/test_E21.py`, `tests/test_E23.py`, `tests/test_e20.py` test specific experiments
- **Adversarial / invalid-chain tests**: `tests/test_adversarial*.py`, `tests/test_invalid_chains.py`
- **Coverage target**: Run with `--cov=adl_lite --cov-report=term-missing`

### Before claiming work complete

```bash
pytest tests/ -v
python -m experiments.runner all
```

## Experiments (28 registered in runner, E1–E30)

```bash
python -m experiments.runner all
```

| ID | Name | Module Under Test |
|----|------|-------------------|
| E1 | Event chain integrity | `EventChain` |
| E2 | Status derivation accuracy | `EventChain` |
| E3 | Snapshot round-trip consistency | `EventChain` + `FrontMatter` |
| E4 | Precondition enforcement | `ActionExecutor` |
| E5 | Multi-agent event chain auditability | `ConsensusEngine` + harness |
| E6 | IBM AML data → ontology pipeline | `DataImporter` + `EventChain` + patterns |
| E6b | Multi-Agent Coordination Efficiency | `ConsensusEngine` |
| E7 | Realtime pattern detection on IBM AML data | `realtime.py` |
| E8 | Edge sync and offline operation | `sync_manager.py` |
| E9 | Git baseline comparison | parser + consensus |
| E10 | Full FDE pipeline | `OntologyManager` + `ActionExecutor` |
| E11 | SideEffectQueue stress test | `ActionExecutor` + side effects |
| E12 | Governance benchmark: ADL Lite vs Nanopubs vs PROV-O | export / benchmark |
| E13 | Long-chain performance degradation | `EventChain` |
| E14 | Colluding validators attack | calibration |
| E15 | Precondition boundary stress | `ActionExecutor` |
| E16 | Multi-agent contention simulation | `ConsensusEngine` |
| E19 | Head-to-head governance benchmark (measured) | benchmark (requires `pygit2`) |
| E20 | L2 Template Compliance Effectiveness | `L2Template` |
| E20b | Calibration Baseline | calibration |
| E21 | 100k Event Stress Test | `EventChain` + cold storage |
| E23 | Concurrent Agent Contention | `SyncManager` + concurrent agents |
| E27 | 1M Event Scale Test | `EventChain` (lock split + incremental verify + compressed cold storage) |
| E28 | 10K Concurrent Agent Contention | `EventChain` split-lock contention |
| E24 | Proof Trace Checker (Randomized) | theorem properties |
| E25 | Microbenchmark: Precondition and Confidence Aggregation | calibration + executor |
| E29 | Vector Index Recall | `VectorIndex` + `EmbeddingBackend` |
| E30 | LLM Normalization | `CanonicalizationEngine` + `VectorIndex` |

**Note**: `E19` imports `pygit2`, which is not listed in `pyproject.toml`. Install it manually (`pip install pygit2`) before running `python -m experiments.runner list` or `all`.

## CI / CD Pipeline

GitHub Actions (`.github/workflows/ci.yml`):

1. **Install**: `pip install -e ".[dev]"`
2. **Run tests** (Python 3.10, 3.11, 3.12 matrix) with coverage → Codecov
3. **Lint**: `ruff check adl_lite/`
4. **Type check**: `mypy adl_lite/ --ignore-missing-imports`
5. **Benchmark**: `python experiments/benchmarks/throughput.py`
6. **Coverage upload** to Codecov on Python 3.12 (`fail_ci_if_error: false`)

Pre-commit hooks (`.pre-commit-config.yaml`):
- `ruff` (lint + auto-fix)
- `ruff-format`
- `mypy` (with `pydantic>=2.0`, `types-PyYAML`, `networkx>=3.0`)

## Docker

`Dockerfile` builds a Python 3.10 slim image with `git` and `curl`, installs `adl-lite` in editable mode with `[dev,experiments]`, and sets the entrypoint to run all experiments.

```bash
docker build -t adl-lite-repro .
docker run --rm -v $(pwd)/docs/experiments:/app/docs/experiments adl-lite-repro
```

## Conventions & Design Rules

- **Event-first**: `status`, `confidence`, and `validators` are derived from `EventChain`, NOT stored. Never mutate `front_matter.status` directly.
- **Status flow**: `provisional` → `validated` / `deprecated` / `forked` / `archived`; status is LUB-monotonic and never regresses.
- **Confidence**: G-Counter max over `VALIDATE` / `SNAPSHOT` events, clamped to `[0, 1]`.
- **Scopes**: `public`, `private/<org>`, `user/<id>`, `shared/<collab>`.
- **Precondition rules**: `Comparator` enum (`EQ`, `NEQ`, `GT`, `GTE`, `LT`, `LTE`, `IN`, `EXISTS`). **NO `eval()`**.
- **Cryptographic chaining**: Each `Event` stores a SHA-256 hash that includes its predecessor's hash and `canon_version`. `EventChain.verify_integrity()` validates the full chain against 12 axioms; it is incremental, verifying only newly appended events when the prefix has already been validated.
- **Thread safety**: `EventChain` uses a split-lock design (`_events_lock` + `_cache_lock`, both `threading.RLock`) to reduce contention. Always acquire in the order `_events_lock` → `_cache_lock`. The split-lock design targets 10k concurrent agents.
- **Incremental integrity cache**: `EventChain` caches the verified prefix. External direct mutation of `_events` invalidates the cache and falls back to a full verification.
- **Synthetic events**: Events reconstructed from YAML front matter during parsing are tagged `synthetic=True` in their payload to distinguish them from agent-authored actions.
- **Front matter is a snapshot**: `ADLFrontMatter` is a derived view of the chain, not the source of truth. Mutate the chain, then call `refresh_snapshot()`.
- **Ontology registry changes**: Any new predicate, action, class, or transition must be reflected in `adl_core_ontology.yaml` and, when applicable, in enum/precondition code.
- **Agent workflow**: Discover → Write → Query schema → Validate strict → Register → Transition → Index → Query (see `docs/AGENT_WORKFLOW.md`).
- **5-agent simulation roles**: Discoverer, Reviewer, Skeptic, Merger, Librarian.

## Security Considerations

- **No `eval()` or `exec()`**: Precondition evaluation uses a closed `Comparator` enum with explicit operator dispatch. Never use dynamic evaluation on user input.
- **Hash integrity**: Event hashes include the previous event's hash and `canon_version`, forming a tamper-evident chain. Any modification breaks `verify_integrity()`.
- **Scope ACL**: `ADLValidator` enforces scope prefix rules (`public`, `private/`, `user/`, `shared/`). Validate scope access before returning document content to an agent.
- **SQL injection prevention**: `memory.py` uses parameterized queries only; `LIKE` wildcards are escaped.
- **CSV/JSON import**: `DataImporter` reads tabular data and maps rows to events. Validate `concept_id_field` and payload shapes before appending to chains in production scenarios.
- **Collusion resistance**: `validate` action requires `validator_count >= N_min` (default 1, configurable via ontology YAML). The bonus-formula `γ_agg` and accuracy-weighted `γ_cal` both mitigate collusion by low-accuracy validators.
- **DID / signatures**: `DIDResolver` supports `did:key`, `did:web`, and `did:ethr`; Ed25519/secp256k1 signature verification via `KeyRegistry`; optional Git signature soft-checks; `TransparencyAnchor` now supports flat and Merkle roots with inclusion proofs; `Event.proof` stores W3C LD-Proofs verified during `verify_integrity()`.

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
│   ├── did_resolver.py
│   ├── exceptions.py
│   ├── fde/               # MVP FDE platform
│   ├── jsonld_export.py
│   ├── key_registry.py
│   ├── l2_template.py
│   ├── logging_config.py
│   ├── memory.py
│   ├── models.py
│   ├── near_duplicate.py
│   ├── ontology.py
│   ├── owl_export.py
│   ├── owl_import.py
│   ├── parser.py
│   ├── prov_export.py
│   ├── rdfstar_export.py
│   ├── realtime.py
│   ├── relation_validator.py
│   ├── shacl_validation.py
│   ├── sync_manager.py
│   ├── tools.py
│   ├── validator.py
│   ├── embeddings.py
│   ├── vector_index.py
│   └── canonicalization.py
├── tests/                 # pytest suite (796 collected, 794 passed + 2 skipped)
├── experiments/           # 26 registered experiments
├── examples/              # Sample ADL Markdown files
├── data/aml/              # AML dataset + concepts
├── docs/                  # Current paper + operational docs
│   ├── paper_ao/          # Active Applied Ontology paper (single source of truth)
│   ├── experiments/       # Current experiment results
│   ├── incident-management/ # Runbooks & SLOs
│   ├── ontology/          # Current ontology artifacts
│   └── AGENT_WORKFLOW.md  # 8-step agent workflow
├── archive/               # Categorized historical files (excluded from lint)
│   ├── paper_versions/    # Superseded paper drafts
│   ├── docs/              # Classified historical docs (plans, releases, research, ...)
│   ├── polish_sections/   # LLM polish intermediate outputs
│   └── tests_backups/     # Backup test files
├── specs/                 # TLA+ formal specifications
├── formal/coq/            # Buildable Coq/Iris proof skeleton
├── scripts/               # Utility scripts (TLC wrapper, etc.)
├── pyproject.toml         # Package config, ruff, mypy
├── Dockerfile             # Reproducibility environment
├── reproduce.sh           # One-command reproduction
├── .github/workflows/ci.yml
└── .pre-commit-config.yaml
```
