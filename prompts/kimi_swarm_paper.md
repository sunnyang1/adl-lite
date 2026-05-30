# Prompt for Kimi Agent Swarm — ADL Lite Paper Generation

You are a team of academic paper-writing agents using agent swarm coordination.
Your task is to generate a complete, publication-ready academic paper
for ESWC/ISWC 2027 based on the ADL Lite project.

## Project Identity

**Name**: ADL Lite — Event-First Operational Ontology  
**GitHub**: https://github.com/sunnyang1/adl-lite  
**Status**: 21 core Python modules, 6 experiments (6/6 PASS), 112 tests pass

## Philosophical Foundation

```
Wittgenstein, Tractatus Logico-Philosophicus §1.1:
"The world is the totality of facts, not of things."
→ 世界是事件的总和，而非事物的总和
→ ADL Lite is event-first: Action Type is primary, objects derive from events
```

This is a deliberate inversion of traditional ontology (including Palantir FDE):
- **Old**: Object Type first → Property Type → Link Type → Action Type (appended later)
- **New**: Action Type first → Object Type exists only as participant in events → Status/confidence/validators are COMPUTED from event chains, never stored as mutable fields

## Reference Files (read these in order)

1. **README.md** — Project overview and architecture
2. **AGENTS.md** — Technical reference for agent authors
3. **docs/paper/EVENT_FIRST_DRAFT.md** — Current paper draft (264 lines, use as base)
4. **docs/experiments/RESULTS_EVENT_FIRST.md** — Detailed experiment results
5. **docs/experiments/experiment_results.json** — Raw experiment metrics
6. **adl_lite/adl_core_ontology.yaml** — Ontology registry (v0.2)
7. **docs/SPEC.md** — Language specification
8. **docs/proposals/ONTOLOGY_MIDDLE_LAYER.md** — Architecture rationale

## Key Architectural Innovations (4 contributions)

### 1. EventChain: Cryptographic Append-Only Concept Representation
- Every concept is an EventChain, not a mutable object
- Events linked by `previous_event_id` + SHA-256 hash
- `chain.status` is COMPUTED from lifecycle events (not stored as field)
- `chain.confidence` derived from validate events
- `chain.validators` accumulated from lifecycle events
- `chain.verify_integrity()` detects tampering

### 2. L4 Action Blocks with Structured Precondition Validation
- Actions declared as Markdown fenced blocks in concept files
- `PreconditionRule` uses typed `Comparator` enum (EQ/NEQ/GT/GTE/LT/LTE/IN/EXISTS)
- NO runtime eval() — all validation is structural and parse-time
- Action definitions centralized in `adl_core_ontology.yaml` (closed core set)
- `ActionExecutor` validates preconditions before dispatching side effects

### 3. Unified Experiment System
- `@register("E1")` decorator-based experiment registry
- `BaseExperiment` → `ExperimentResult` interface
- Single CLI: `python -m experiments.runner all`
- Each experiment in its own file (e1_chain_integrity.py through e6_aml_pipeline.py)
- Results collected in unified JSON: `docs/experiments/experiment_results.json`

### 4. IBM AML Pipeline at Scale
- `DataImporter` ingests CSV → Event objects
- Ontology discovered FROM event payloads (not pre-defined)
- 495,671 accounts → 495,671 EventChains with cryptographic integrity
- 5,080,714 transactions processed in 238 seconds
- Pattern detection cross-references existing AML concept files

## Experiment Results (all 6/6 PASS)

### E1 — Chain Integrity (5ms)
EventChain.verify_integrity() tested: 50 valid chains → 100% pass; 10 corrupt chains (broken previous_event_id, payload tampering, cross-contamination) → 100% detected.

### E2 — Status Derivation Accuracy (79ms)
Exhaustive enumeration of 2,204 event sequences (13^3 = 2,197 + 7 edge cases). EventChain.status matches ground truth in all 2,204 cases. Communication events (ANNOUNCE, PUBLISH) never affect status — only lifecycle events (REGISTER, VALIDATE, DEPRECATE, FORK, ARCHIVE) do.

### E3 — Snapshot Round-Trip (25ms)
All 38 concept files parsed → EventChain → FrontMatter snapshot. Status preserves 100%. Confidence preserves 100%. Pre-L4 concept files without action blocks show validators divergence (expected — incomplete event history).

### E4 — Precondition Enforcement (4ms)
13 test cases across 9 registered actions. Precision 1.0, Recall 1.0, F1 1.0. Zero false positives (no action incorrectly allowed). Zero false negatives (no action incorrectly blocked). Unknown actions correctly rejected.

### E5 — Multi-Agent Auditability (13ms)
5-agent ScriptedHarness over 5 concepts. All 5 chains pass verify_integrity(). Harness produces 15 SimEvents; 9 are lifecycle events.

### E6 — IBM AML Pipeline (238,490ms / ~4 min)
Real IBM AML HI-Small dataset: 495,671 accounts, 5,080,714 transactions.
- ALL 495,671 chains pass verify_integrity()
- 3,386 suspicious accounts detected
- 3,386/3,386 suspicious chains integrity OK
- 8,376 laundering events (0.16%)
- 4 pattern types detected matching existing AML concepts:
  - High frequency (≥10 laundering events): 11 accounts → aml-rapid-move
  - Cyclic (money returns to origin): 11 accounts → aml-cyclic-pattern
  - Fan-out (≥5 unique recipients): 3 accounts → aml-fan-out-pattern
  - Smurfing (sub-$1000 structuring): 1 account → aml-smurfing

## Paper Structure (ESWC/ISWC 2027)

### Title (suggested)
"Event-First Operational Ontology: Cryptographic Event Chains for Multi-Agent Concept Consensus"

### Abstract (key claims)
- Event-first: concepts are EventChains, status derived not stored
- Structured preconditions with Comparator enum (no eval())
- 6 experiments, all pass; IBM AML at scale (495K chains, zero failures)
- Palantir FDE comparison: same ontology primitives, Markdown-native, Git-backed, pip-installable
- Wittgenstein §1.1 as philosophical grounding

### Sections
1. **Introduction** — Multi-agent discovery problem, event-first philosophy, 4 contributions
2. **Architecture** — EventChain design, L1-L4 document model, PreconditionRule, ActionExecutor
3. **Related Work** — Palantir FDE, ontology construction, multi-agent consensus, AML case studies
4. **Experiment Design** — E1-E6 methods, unified runner, dataset description
5. **Results** — All 6 experiment metrics, IBM AML at scale, pattern detection
6. **Discussion** — Palantir comparison, limitations (stub side effects), future work
7. **Conclusion** — Event-first validated at scale, pip-installable, LLM-native

### Venue Fit
- Primary: ESWC 2027 (Semantic Web, ontology engineering, knowledge graphs)
- Primary: ISWC 2027 (operational ontology, agentic KG)
- Backup: AAMAS 2027 (multi-agent consensus, coordination)
- Relevant tracks: In-Use, Resource, Research

### Key Arguments to Make
1. Wittgenstein's event-first philosophy is not just theory — it produces measurable integrity guarantees
2. Cryptographic chain integrity scales to 500K chains without degradation
3. Structured preconditions (Comparator enum, no eval()) achieve 100% precision/recall
4. Palantir FDE's ontology layer can be replicated as Markdown-native, Git-backed, pip-installable
5. LLM agents can author ontology documents because they're Markdown (not UI/SDK)
6. Zero chain failures in real IBM AML data proves the architecture is production-ready at this scale

### Negative Results / Honest Limitations
- Side effects (Lark announce/publish/dashboard) are connected but not stress-tested with real IM
- ConsensusEngine still mutates FrontMatter directly in harness (not yet fully event-driven)
- Ontology discovery uses simple _id suffix matching (not production-grade)
- IBM AML pattern detection is synthetic-injection-aware (needs real typology calibration)
- No human inter-rater validation (LLM-as-judge only from old RQ1 experiments)

### What NOT to Claim
- NOT a new multi-agent orchestration framework
- NOT production AML compliance
- NOT a replacement for Palantir FDE (complementary layer)
- NOT OWL reasoning or automatic hierarchy induction
- NOT benchmark-leading performance (correctness-first, not speed-first)

## Agent Swarm Task Assignment

Assign these subtasks to your swarm agents:

**Agent A — Philosophy & Architecture**: Write Introduction (Wittgenstein grounding), Architecture section (EventChain + L1-L4 + PreconditionRule)

**Agent B — Related Work**: Write Related Work (Palantir FDE comparison, ontology construction methods, AML context)

**Agent C — Experiment Design & Results**: Write Method (E1-E6 design and execution) and Results section from experiment_results.json

**Agent D — Discussion & Conclusion**: Write Discussion (limitations, Palantir comparison table) and Conclusion

**Agent E — Abstract & Polish**: Merge all sections, write Abstract, enforce ESWC/ISWC formatting, check claims vs evidence tables

### Coordination Rules
- All agents must read `docs/paper/EVENT_FIRST_DRAFT.md` as baseline
- Agent C must read `docs/experiments/experiment_results.json` for numbers
- Agent B must read `docs/proposals/ONTOLOGY_MIDDLE_LAYER.md` for Palantir comparison
- All numbers must match the experiment_results.json exactly
- Use LaTeX for final output
- Target length: 8-10 pages (ESWC/ISWC format)

## Validation Checklist (before declaring done)

- [ ] All 6 experiment metrics present and correct
- [ ] E6 scale numbers (495,671 chains, 5.08M events, 0 failures) highlighted
- [ ] Wittgenstein citation accurate (Tractatus §1.1)
- [ ] Palantir FDE comparison table present
- [ ] PreconditionRule 100% P/R/F1 claimed
- [ ] Chain integrity at scale claimed
- [ ] Limitations section honest about stubs and harness integration
- [ ] Target venue (ESWC/ISWC 2027) stated
- [ ] No claims about OWL reasoning, production AML, or multi-agent orchestration
