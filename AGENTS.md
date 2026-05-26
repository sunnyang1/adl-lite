# ADL Lite — Agent Guide

Markdown-native **operational ontology** for agentic KG authoring and multi-agent concept consensus (primary: ESWC + ISWC 2027; backup: AAMAS 2027).

## Architecture

| Module | Role |
|--------|------|
| `adl_lite/parser.py` | L1 YAML front matter, L2 Markdown body, L3 `adl:*` fenced blocks, wiki-link extraction |
| `adl_lite/models.py` | Pydantic types (`ADLDocument`, relations, evidence, seals) |
| `adl_lite/validator.py` | SSA semantic validation + scope ACL |
| `adl_lite/consensus.py` | Status transitions, forks, chain integrity |
| `adl_lite/memory.py` | Hot/Warm/Cold hybrid index (`ADLMemory`) |
| `adl_lite/tools.py` | Agent-facing wrappers matching CLI semantics |
| `experiments/harness.py` | Scripted 5-agent simulation |

Public API: `from adl_lite import parse_file, ADLMemory, ConsensusEngine, ...` (see `adl_lite/__init__.py`).

## Commands

```bash
pip install -e ".[dev]"
pytest tests/ -v
pytest experiments/ -v
ruff check adl_lite tests experiments
adl-lite validate examples/*.md
adl-lite validate --strict examples/*.md
adl-lite ontology validate
adl-lite ontology validate --examples
adl-lite parse examples/capital_reflux_trap.md
adl-lite store examples/capital_reflux_trap.md --db /tmp/adl.db
adl-lite related concept-gradient-explosion --db /tmp/adl.db
adl-lite consensus register examples/capital_reflux_trap.md
adl-lite lark doctor
adl-lite lark publish examples/capital_reflux_trap.md --registry .adl_lark_registry.json
adl-lite lark sync-memory --db /tmp/adl.db --base "AML概念知识库" --mode warm [--table concepts] [--dry-run]
adl-lite lark announce disc-capital-trap --chat-id oc_xxx [--template discovery_broadcast]
adl-lite lark listen --feedback-file feedback.txt --auto-transition --threshold 2 --state adl_consensus.json
adl-lite lark init-dashboard --sheet "AML概念共识看板" --db /tmp/adl.db --columns "concept_id,status_badge,confidence,discoverer,validators,last_update,doc_link"
adl-lite lark map-namespace --scope private/ceiec-aml --wiki-space <id>
adl-lite lark namespace list|set adl://private/ceiec-aml/ <wiki_space>
adl-lite consensus transition disc-capital-trap --to validated --actor agent_1 --lark-sync --sheet "AML概念共识看板" --db /tmp/adl.db
python -m experiments.run_sim --scripted
python -m experiments.run_all
```

Spec: `docs/SPEC.md`. PRD: `docs/PRD.md`. Implementation plan: `docs/IMPLEMENTATION_PLAN.md` (Phase 2+ ontology 2a–2c). Ontology proposal: `docs/proposals/ONTOLOGY_MIDDLE_LAYER.md`. Agent workflow: `docs/AGENT_WORKFLOW.md`. CLI entry: `adl_lite/cli.py`.

## Agent tools (Python)

```python
from adl_lite.tools import adl_parse, adl_validate, adl_store, adl_query_related
from adl_lite.tools import adl_consensus_register, adl_consensus_transition
```

Optional MCP-style script: `scripts/mcp_adl.py` (stdio JSON: `adl_parse`, `adl_validate`, `adl_query_related`).

**Lark bridge** (requires [lark-cli](https://github.com/larksuite/cli)): `adl_lite/lark/` wraps lark-cli for publish (docs v2), sync-memory (base), announce/listen (im), init-dashboard (sheets), and namespace mapping.

Setup (once per machine):

```bash
lark-cli config init --app-id <id> --app-secret-stdin --brand feishu
lark-cli auth login --recommend
# IM announce also needs:
lark-cli auth login --scope "im:message.send_as_user"
adl-lite lark doctor
```

Local state (gitignored): `.adl_lark_registry.json` (doc_id, base tokens, dashboard `sheet_id`); `.adl_lark_namespaces.json` (scope → wiki space).

Operational notes:

| Topic | Guidance |
|-------|----------|
| Batch publish | Sleep **≥4s** between `adl-lite lark publish` calls to avoid Feishu rate limit `99991400` |
| `--lark-sync` | Requires dashboard entry in registry with resolved `sheet_id` (auto-fetched via `sheets +info` on first sync) |
| Base sync | Register base name → token in registry `bases` after `lark-cli base +base-create` |
| Bot vs user | `announce` uses user identity; bot must be in chat if using `--as bot` |

## ADL document shape

- **L1**: YAML with `adl_type`, `adl_id`, `status`, `confidence`, `scope`, etc.
- **L2**: Markdown body (human/LLM prose, `[[Wiki Links]]`)
- **L3**: Fenced blocks like ` ```adl:relation `, ` ```adl:evidence `, ` ```adl:formal_seal `

Examples:

| File | Role |
|------|------|
| `examples/capital_reflux_trap.md` | Private AML discovery |
| `examples/gradient_explosion.md` | Public concept |
| `examples/attention_residual_discovery.md` | Private ML discovery |
| `examples/matdo_original.md` + `matdo_fork_kinetic.md` | Fork pair |

Prompt template: `prompts/write_discovery.md`

## Conventions

- Python 3.10+, Pydantic v2, NetworkX for graph ops
- Status flow: `provisional` → `validated` / `deprecated` / `forked` / `archived`
- Scopes: `public`, `private/<org>`, `user/<id>`, `shared/<collab>`
- Prefer surgical changes; match existing module boundaries
- Run `pytest tests/ -v` and `adl-lite validate examples/*.md` before claiming work complete

## Evaluation & dataset

- AML mini-dataset: `data/aml/` (20 concepts, 15 queries) — `data/aml/loader.py`
- Pilot results: `docs/experiments/RESULTS.md`
- Paper pack: `docs/paper/OUTLINE.md`, `docs/RESEARCH_STATEMENT.md`

## Roadmap status

Phase 1 (May–Jun 2026): parser + hybrid index + 5-agent scripted sim + AML dataset + pilot RQ1–RQ4.

Phase 2+ (ontology track): `adl_core_ontology.yaml` (2a) → `OntologyManager` + validator integration (2b) → `adl_ontology_query` (2c) → optional Turtle export (Phase 3). See `docs/PRD.md` §3.
