# ADL Lite — Experiment Results (Event-First Ontology)

**Run date**: 2026-05-30  
**Experiment runner**: `python -m experiments.runner all`  
**Method**: `adl_core_ontology.yaml` v0.2 (L4 action registry)  
**Ontology philosophy**: Wittgenstein Tractatus §1.1 — "The world is the totality of facts, not of things."

---

## Summary

| Experiment | Status | Duration | Key Metric |
|-----------|--------|----------|------------|
| E1 — Chain Integrity | PASS | 5ms | Precision 1.0, Recall 1.0 |
| E2 — Status Derivation | PASS | 81ms | 2204/2204 correct (100%) |
| E3 — Snapshot Roundtrip | PASS | 25ms | 38/38 status match (100%) |
| E4 — Precondition Enforcement | PASS | 4ms | Precision 1.0, Recall 1.0, F1 1.0 |
| E5 — Multi-agent Audit | PASS | 12ms | 5/5 chains integrity OK |

**Total runtime**: 127ms for all 5 experiments.

---

## E1 — Event Chain Integrity

**Question**: Does `EventChain.verify_integrity()` correctly detect chain tampering?

**Method**:
- Generated 50 valid random chains (5 events each, 6 event types)
- Injected 10 corruptions using 3 methods: broken `previous_event_id`, payload tampering without re-hash, cross-contamination `concept_id`

**Results**:

| Metric | Value |
|--------|-------|
| Valid chain pass rate | 1.0 (50/50) |
| Corrupt chain detection rate | 1.0 (10/10) |
| Valid chains tested | 50 |
| Corrupt chains tested | 10 |

**Interpretation**: The cryptographic event chain correctly detects all three classes of tampering. Method c (cross-contamination) is caught at `EventChain.append()` time by the `concept_id` check, preventing the event from entering the chain at all. Methods a and b are detected by `verify_integrity()` post-hoc.

---

## E2 — Status Derivation Accuracy

**Question**: Does `EventChain.status` always compute the correct `DiscoveryStatus` from any event sequence?

**Method**: Exhaustive enumeration of all 3-event sequences (13^3 = 2197) + 7 edge cases including empty chain, single event, full lifecycle, and communication-only chains. Ground truth: the last lifecycle event in the sequence determines status.

**Results**:

| Metric | Value |
|--------|-------|
| Total cases | 2,204 |
| Correct | 2,204 |
| Accuracy | 1.0 |
| Errors | 0 |

**Verified edge cases**:
- Empty chain → `PROVISIONAL`
- `[REGISTER]` → `PROVISIONAL`
- `[REGISTER, VALIDATE]` → `VALIDATED`
- `[REGISTER, FORK]` → `FORKED`
- `[REGISTER, VALIDATE, DEPRECATE]` → `DEPRECATED`
- `[REGISTER, ANNOUNCE, PUBLISH]` → `PROVISIONAL` (comms don't change status)
- `[REGISTER, VALIDATE, RELATE]` → `VALIDATED` (relate preserves status)

**Interpretation**: Status derivation is deterministic and correct for all 2,204 event combinations. Communication events (ANNOUNCE, PUBLISH, RELATE, EVIDENCE) never affect status — only lifecycle events (REGISTER, VALIDATE, DEPRECATE, FORK, ARCHIVE) do. This confirms that the event-first architecture can safely remove `FrontMatter.status` as a storage field and instead compute it from the chain.

---

## E3 — Snapshot Round-trip Consistency

**Question**: Does `parse_file → event_chain → FrontMatter.from_chain()` preserve status/confidence/validators?

**Method**: Tested all 38 ADL concept files (`examples/` + `data/aml/concepts/`). Each file was parsed, its event chain built, and front matter re-derived from the chain.

**Results**:

| Metric | Value |
|--------|-------|
| Total files | 38 |
| Status match | 38 (100%) |
| Confidence match | 38 (100%) |
| Status accuracy | 1.0 |

**Status distribution in test corpus**:
- `provisional`: 6 files
- `validated`: 30 files
- `forked`: 1 file

**Interpretation**: The round-trip is lossless for status and confidence. Validators show divergence on some files where the parsed front matter lists validators but the event chain lacks explicit VALIDATE events (these concepts were imported with `status: validated` in L1 but no L4 action block records the validation event). This is expected — it reflects the incomplete event history in the pre-L4 corpus, not a bug in the chain logic.

---

## E4 — Precondition Enforcement

**Question**: Does `ActionExecutor.validate_action()` correctly enforce preconditions, required parameters, and action name validation?

**Method**: 13 test cases covering all 9 core actions. Each case generates a document with specific confidence/status/params combinations and checks whether the action is correctly allowed or blocked.

**Results**:

| Metric | Value |
|--------|-------|
| True Positive (correctly allowed) | 5 |
| False Positive (incorrectly allowed) | 0 |
| True Negative (correctly blocked) | 8 |
| False Negative (incorrectly blocked) | 0 |
| Precision | 1.0 |
| Recall | 1.0 |
| F1 | 1.0 |

**Blocked cases verified**:
- `validate` blocked when `confidence < 0.5`
- `validate` blocked when `status != provisional`
- `deprecate` blocked when `status != validated`
- `deprecate` blocked when `reason` param missing
- `fork` blocked when `status != validated`
- `archive` blocked when `status != deprecated`
- `announce` blocked when `chat_id` param missing
- `nonexistent_action` rejected as unknown

**Interpretation**: All precondition rules, required parameter checks, and action name validations function correctly. The structured `Comparator` enum + `PreconditionRule` Pydantic model achieves 100% precision and recall without runtime `eval()`.

---

## E5 — Multi-agent Event Chain Auditability

**Question**: Can the 5-agent ScriptedHarness simulation produce auditable event chains that pass integrity verification?

**Method**: Ran the existing 5-agent simulation (Discoverer, Reviewer, Skeptic, Merger, Librarian) over 5 example concepts. Each concept's Markdown file was then parsed into an `EventChain`, and chains were verified for integrity, coverage, and lifecycle tracking.

**Results**:

| Metric | Value |
|--------|-------|
| Chains tested | 5 |
| Chains passing integrity | 5 (100%) |
| Average chain length | 5.4 events |
| SimEvents produced | 15 |
| Lifecycle SimEvents | 9 |
| Lifecycle chain events | 2 |

**Per-concept results**:

| Concept | Chain Length | Integrity | Status |
|---------|-------------|-----------|--------|
| `disc-capital-trap` | 7 | OK | provisional |
| `concept-gradient-explosion` | 4 | OK | validated |
| `disc-attention-residual` | 5 | OK | provisional |
| `disc-matdo-original` | 6 | OK | forked |
| `disc-matdo-kinetic` | 5 | OK | provisional |

**Interpretation**: All chains pass integrity verification. The gap between SimEvents (15) and lifecycle chain events (2) reflects that the current harness modifies status via `ConsensusEngine.transition()` rather than appending events to the chain — a remaining integration point. The harness auditability is structurally sound; the next step is to wire `ConsensusEngine` to produce `Event` objects directly rather than mutating `FrontMatter.status`.

---

## Design Limitations & Next Steps

1. **E3 validators divergence**: Pre-L4 concept files (AML corpus) lack action blocks. Status reconstruction from `from_parsed()` correctly preserves status but cannot recover validator identity without VALIDATE events in the file.

2. **E5 harness integration**: `ScriptedHarness` uses `ConsensusEngine.transition()` which mutates `FrontMatter.status` directly. Full auditability requires the harness to append `Event` objects to the chain via `ActionExecutor`.

3. **Side-effect stubs**: All side-effect backends (Lark announce/publish/dashboard) are stubs that return success without executing real integrations. Full system testing requires real Lark backend wiring.

4. **E5 coverage gap** (4/5): One concept file's `adl_id` does not appear in SimEvents because the harness only generates events for concepts it explicitly operates on.
