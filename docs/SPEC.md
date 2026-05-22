# ADL Lite — Normative Specification (v0.1)

This document is the authoritative syntax and semantics reference for **ADL Lite** (Agent Discovery Language, Lite edition). It aligns with `adl_lite/models.py` and supersedes the long design transcript for day-to-day implementation.

**URI namespaces** (logical, used in relation targets and documentation):

- `adl://public/…` — world-readable concepts
- `adl://private/<org>/…` — organization-private
- `adl://user/<id>/…` — single-user private
- `adl://shared/<collab>/…` — collaboration group

**L1 scope field** uses slash paths without the `adl://` prefix: `public`, `public/…`, `private/<org>`, `user/<id>`, `shared/<collab>`.

---

## 1. Document types (`adl_type`)

| Value | Role |
|-------|------|
| `discovery` | New phenomenon or pattern reported by an agent |
| `concept` | Stable concept definition (often public) |
| `relation` | Standalone edge document (optional) |
| `evidence` | Standalone evidence record (optional) |
| `formal_seal` | Standalone formal assertion (optional) |

Most files are `discovery` or `concept`. L3 blocks may embed relations and evidence inside any document type.

---

## 2. L1 — YAML front matter

Required for all documents:

| Field | Type | Rules |
|-------|------|--------|
| `adl_type` | enum | One of §1 |
| `adl_id` | string | `^[a-zA-Z0-9_-]+$`, unique in a corpus |
| `status` | enum | See §5 |
| `confidence` | float | `[0, 1]` |
| `novelty` | float | `[0, 1]` |
| `scope` | string | See §4 |
| `provisional_names` | object | At least one of `zh`, `en` non-empty |

Common optional fields: `domain`, `mechanism`, `validators`, `evidence_refs`, `created_at`, `updated_at`.

**Type-specific L1 rules:**

- `discovery` — `mechanism` required (`isomorphic_mapping`, `analogical_transfer`, `compositional_blend`, `abstract_generalisation`, `emergent_pattern`).
- `formal_seal` — in strict validator mode, `validators` list should be non-empty.

Documents are wrapped in standard YAML front matter delimiters:

```yaml
---
adl_type: discovery
adl_id: disc-example
...
---
```

---

## 3. L2 — Markdown body

Human- and LLM-readable prose: headings, lists, block quotes, `[[Wiki Links]]`.

**Pronoun prohibition (SSA):** The definition / discovery narrative must not use fuzzy referents that break cross-agent alignment. Forbidden tokens include (case-insensitive, word boundaries): `this`, `that`, `it`, `these`, `those`, and Chinese equivalents (`这个`, `那个`, `它`, `它们`, `这里`, `那里`). Use explicit concept names or `adl://` URIs instead.

Wiki links are compatible with LLM Wiki v2; semantic edges should still be declared in L3 `adl:relation` blocks for machine consumption.

---

## 4. Scope grammar

L1 `scope` must match:

```text
public | public/<path> | private/<org> | user/<id> | shared/<collab>
```

Where `<org>`, `<id>`, `<collab>` are `[a-zA-Z0-9_-]+`.

**Access control** (`validate_scope_access(doc_scope, requester_scope)`):

| Document scope | Who may read |
|----------------|--------------|
| `public` or `public/…` | Any requester |
| `private/X` | Only `private/X` |
| `user/U` | Only `user/U` |
| `shared/S` | Only `shared/S` (exact match) |

Cross-scope **relation targets** may point at `adl://public/…` from private documents; evidence and full document retrieval still obey the table above.

---

## 5. Status machine

| Status | Badge | Meaning |
|--------|-------|---------|
| `provisional` | 🟡 | Default; awaiting review |
| `validated` | 🟢 | Accepted by consensus |
| `deprecated` | 🔴 | Superseded or rejected |
| `forked` | 🔵 | Competing interpretation exists |
| `archived` | ⚪ | Terminal; retained for lineage |

**Valid transitions** (enforced by `ConsensusEngine`):

```text
provisional → validated | deprecated | forked | archived
validated     → deprecated | forked | archived
forked        → validated | deprecated | archived
deprecated    → archived
archived      → (none)
```

Fork workflow: original concept → `forked`; new `adl_id` gets a new chain starting at `provisional`. Resolution strategies (merge / parallel / prune) are policy-level; v0.1 records transitions only.

---

## 6. L3 block schemas

Fenced blocks use the form ` ```adl:<subtype> ` with YAML-like `key: value` lines inside.

### 6.1 `adl:relation`

| Field | Required | Description |
|-------|----------|-------------|
| `source` | yes | Source concept label (no pronouns) |
| `relation` | yes | Predicate, e.g. `isomorphic-to`, `specialisation-of` |
| `target` | yes | Target label or `adl://…` URI |
| `mapping_type` | no | e.g. `topological`, `ontological` |
| `confidence` | no | `[0, 1]`, default `1.0` |

Targets starting with `adl://` must match `^adl://(public|private|user|shared)/`.

### 6.2 `adl:evidence`

| Field | Required | Description |
|-------|----------|-------------|
| `evidence_type` | yes | `vector_cluster`, `simulator_run`, `human_expert`, `cross_reference`, `empirical_observation` |
| `data_ref` | yes | URI: `vecdb://`, `tool://`, `expert://`, `file://`, etc. |
| `description` | no | Human-readable summary |
| `confidence` | no | `[0, 1]` |
| `observed_at` | no | ISO-8601 timestamp |

L1 `evidence_refs` may duplicate pointers for index-friendly listing.

### 6.3 `adl:seal` (formal seal)

| Field | Required | Description |
|-------|----------|-------------|
| `assertion` | yes | Formal claim identifier or statement |
| `language` | no | `lean4` (default), `coq`, `z3`, `fol` |
| `proof_ref` | no | URL or path to proof artifact |
| `status` | no | `pending`, `verified`, `failed` |
| `verified_by` | no | Agent or human verifier id |

v0.1 stores references only; proof execution is out of scope.

---

## 7. Validation rules (summary)

The `ADLValidator` returns a list of error strings (empty ⇒ pass):

1. **L1** — scope pattern; confidence/novelty range; discovery `mechanism`; provisional name present.
2. **L2** — forbidden pronouns in body.
3. **L3** — non-empty relation source/target; valid `adl://` target scheme; Pydantic blocks reject pronouns in source/target slots.

`ADLValidator(strict=True)` enables extra checks (e.g. formal seal validators list).

Parse-time validation: invalid enum values or malformed YAML raise `ADLParseError` / Pydantic errors.

---

## 8. Storage model (informative)

- **Hot** — in-memory `ConceptSkeleton` per `adl_id`.
- **Warm** — SQLite + optional NetworkX graph for documents and relations.
- **Cold** — file archive (not required in v0.1).

`ADLMemory.store(doc)` writes skeleton + full document + relation edges.

---

## 9. v0.1 non-goals

| Deferred | Reason |
|----------|--------|
| Lean4 / Coq / Z3 execution | Seals are references only |
| FAISS / vector ANN in warm layer | Graph + SQL sufficient for Phase 1 |
| Full S-expression ADL syntax | Markdown-native path is the product |
| MCP server / production Harness | Phase 3+ |
| Automatic wiki-link → relation extraction | Optional post-pass later |
| Round-trip Markdown serializer | Stretch goal |

---

## 10. Example conformance

The reference discovery `examples/capital_reflux_trap.md` demonstrates L1 discovery metadata, L2 prose without pronouns, L3 relations/evidence/seal, and `private/ceiec-aml` scope with `adl://public/…` targets.

**Smoke test:**

```bash
pip install -e ".[dev]"
adl-lite validate examples/*.md
pytest tests/ -v
```

---

*Version 0.1.0 — aligned with `adl_lite` package. Design provenance: `ADL_Lite_对话全记录.md` §6–§8.*
