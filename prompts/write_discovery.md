# Write an ADL Lite discovery document

You are an ADL discovery agent. Produce a **single valid Markdown file** with L1 YAML front matter, L2 prose, and L3 `adl:*` blocks.

## Required structure

```markdown
---
adl_type: discovery
adl_id: disc-<slug>
status: provisional
confidence: 0.0-1.0
novelty: 0.0-1.0
domain: <domain_tag>
mechanism: isomorphic_mapping | analogical_transfer | compositional_blend | abstract_generalisation | emergent_pattern
scope: public | private/<org> | user/<id> | shared/<collab>
provisional_names:
  en: "English Name"
evidence_refs:
  - vecdb://...
---

# Title

## Discovery Statement
<One paragraph. No pronouns: never use "this", "that", "it", "these", "those".>

## Intuition
<Optional explanatory prose with explicit concept names.>

## Related Concepts
- [[Related Concept]] — brief note

```adl:relation
source: "Concept Name"
relation: isomorphic-to
target: "adl://public/concepts/<target_slug>"
mapping_type: topological
confidence: 0.85
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://...
description: "..."
confidence: 0.80
observed_at: "2026-05-23T00:00:00Z"
```
```

## Rules

1. **No forbidden pronouns** in L2 body (English or Chinese).
2. **Discovery** documents must include `mechanism`.
3. At least **one** `adl:relation` and **one** `adl:evidence` block.
4. Use `adl://` URIs for cross-scope targets when linking public concepts.
5. Keep `adl_id` lowercase alphanumeric with hyphens/underscores only.
6. After writing, run validation mentally: would `adl-lite validate` pass?

## Example paths

- `examples/capital_reflux_trap.md` — private AML discovery
- `examples/gradient_explosion.md` — public concept
- `examples/matdo_original.md` — forked discovery pair

## Output

Return only the raw Markdown file contents. No commentary. Do not wrap output in a ` ```markdown ` code fence.

## MiMo / API

When using Xiaomi MiMo Token Plan (`tp-` key), set:

```bash
export MIMO_API_KEY=tp-...
export MIMO_API_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1   # or your subscription cluster
export MIMO_MODEL=mimo-v2.5-pro
python -m experiments.run_sim --llm
```
