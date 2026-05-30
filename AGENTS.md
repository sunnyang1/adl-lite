# ADL Lite — Agent Guide

Markdown-native **event-first operational ontology** for agentic KG authoring and multi-agent concept consensus (primary: ESWC + ISWC 2027; backup: AAMAS 2027).

Philosophy: Wittgenstein Tractatus §1.1 — "The world is the totality of facts, not of things." → Action-first. Concepts are event chains.

## Architecture

| Module | Role |
|--------|------|
| `adl_lite/parser.py` | L1 YAML, L2 Markdown body, L3 `adl:*` blocks, L4 `adl:action` blocks |
| `adl_lite/models.py` | Pydantic types (`Event`, `EventChain`, `ADLDocument`, L3 blocks, L4 action blocks, `PreconditionRule`) |
| `adl_lite/validator.py` | SSA semantic validation + scope ACL |
| `adl_lite/consensus.py` | Status transitions, forks, chain integrity |
| `adl_lite/action_executor.py` | Action validation (preconditions) + side-effect dispatch |
| `adl_lite/data_importer.py` | CSV/JSON → Event import + ontology discovery |
| `adl_lite/ontology.py` | `OntologyManager` — predicates, actions, transitions from YAML registry |
| `adl_lite/memory.py` | Hot/Warm/Cold hybrid index (`ADLMemory`) |
| `adl_lite/tools.py` | Agent-facing wrappers matching CLI semantics |
| `experiments/harness.py` | Scripted 5-agent simulation |

Public API: `from adl_lite import parse_file, Event, EventChain, ActionExecutor, ADLMemory, ConsensusEngine, ...`

## Event-First Design

```python
from adl_lite import Event, EventChain, EventType, DiscoveryStatus

# Concept = EventChain (not mutable object)
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

## Commands

```bash
pip install -e ".[dev]"
pytest tests/ -v

# CLI
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md
adl-lite parse examples/capital_reflux_trap.md
adl-lite store examples/capital_reflux_trap.md --db /tmp/adl.db
adl-lite related concept-gradient-explosion --db /tmp/adl.db
adl-lite consensus register examples/capital_reflux_trap.md
adl-lite consensus transition disc-capital-trap --to validated --actor agent_1

# Ontology
adl-lite ontology validate
adl-lite ontology query --json
adl-lite ontology query --predicate isomorphic-to

# Lark bridge
adl-lite lark doctor
adl-lite lark publish examples/capital_reflux_trap.md --registry .adl_lark_registry.json

# Experiments
python -m experiments.runner list
python -m experiments.runner all
python -m experiments.runner E6 --verbose
```

## Agent tools (Python)

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
```

## ADL document shape (L1/L2/L3/L4)

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

## Ontology registry (adl_core_ontology.yaml v0.2)

Closed sets:
- **classes**: discovery, concept, relation, evidence, formal_seal
- **predicates**: isomorphic-to, specialisation-of, co-occurs-with, related-to, analogical-to, analogical-transfer, dual-of, fork-of, mitigated-by, indexed-phrase
- **actions**: register, validate, fork, deprecate, archive, announce, publish, sync_dashboard, listen
- **status_transitions**: provisional→validated/deprecated/forked/archived, validated→deprecated/forked/archived, ...

## Experiments (6/6 PASS, 238s)

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

## Conventions

- Python 3.10+, Pydantic v2, NetworkX for graph ops
- Event-first: status/confidence/validators derived from EventChain, NOT stored
- Status flow: `provisional` → `validated` / `deprecated` / `forked` / `archived`
- Scopes: `public`, `private/<org>`, `user/<id>`, `shared/<collab>`
- Precondition rules: `Comparator` enum (EQ/NEQ/GT/GTE/LT/LTE/IN/EXISTS), NO eval()
- Run `pytest tests/ -v` and `python -m experiments.runner all` before claiming work complete
