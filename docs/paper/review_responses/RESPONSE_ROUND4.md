# Response to Reviewer — Round 4

**Paper:** Event-First Operational Ontology: Cryptographic Event Chains for Multi-Agent Concept Consensus  
**Venue:** ESWC / ISWC 2027 (full paper)  
**Target journal (post-conference):** Applied Ontology  
**Date:** 2026-06-01

---

## Cover Letter

We thank the reviewer for the exceptionally thorough and constructive critique. This response addresses every major concern with concrete changes to the code, the paper, and the artifact. The three most significant corrections are:

1. **Hash canonicalization**: The paper incorrectly stated that timestamps are excluded from the SHA-256 hash input. The code has always included timestamps in the hash; we have corrected the paper to reflect this accurately and have now added the six-decimal float normalization that the paper already claimed.

2. **Experiment count and scale**: The paper alternately reported nine and eleven experiments, and E6 scale numbers were inconsistent (201 accounts in the code vs. 495,671 in the paper). We have reconciled all claims to match the actual codebase: **eleven experiments** (E1–E11), with E6 operating on the publicly available HI-Small sample of **201 accounts / 9,300 transactions**.

3. **Sybil resistance**: We have renamed Corollary 2 to "Bounded Confidence Aggregation per Distinct Actor" and explicitly scoped full Sybil resistance to Phase 3 cryptographic identity (Linked Data Proofs + ed25519).

A full changes checklist is provided at the end of this document.

---

## 1. Timestamp Exclusion from Hash Input

**Reviewer concern:** "Excluding timestamps from the hash input undermines tamper-evidence for a key provenance field; this is a nontrivial integrity hole for many audit use cases."

**Response:** The reviewer is absolutely correct that excluding timestamps from the hash would create an integrity hole. We are pleased to report that **the implementation already includes timestamps in the hash** (`models.py:149`). The paper was incorrect in stating they were excluded. We have:

- Corrected Section 3.3.1 and Section 3.3.2 in both the `.md` and LaTeX (v3) versions to state that timestamps **are** included in the hash input.
- Added Proposition 3 (Timestamp Integrity): "Any modification to an event's timestamp field changes its hash."
- Clarified that clock-skew tolerance is achieved by defining event ordering through `previous_event_id` cryptographic linkage (which is independent of wall-clock time), not by excluding timestamps from the hash.
- Updated the canonical serialization formula to: `b = UTF-8(JSON-SORTED(e \ {hash}))`.

This design gives us the best of both properties: timestamps are integrity-protected (any edit is detectable), yet clock skew cannot cause spurious chain forks because ordering is defined by cryptographic linkage.

---

## 2. Sybil-Resistant Aggregation (Corollary 2)

**Reviewer concern:** "A claim of 'Sybil-resistant aggregation' is difficult to justify when actor identity is an unauthenticated string; without cryptographic identity binding, Sybil-resistance is not credible."

**Response:** We agree entirely. We have:

- Renamed Corollary 2 to **"Bounded Confidence Aggregation per Distinct Actor"**.
- Added an explicit caveat in the proof text: "Full Sybil resistance—preventing an adversary from creating arbitrarily many distinct actor identities to inflate confidence—requires cryptographic actor authentication (Phase 3; Section 3.7). In Phase 1, the bound provides Sybil *awareness* (redundant events from the same unauthenticated actor string do not compound) but not Sybil *resistance* under adversarial identity fabrication."
- Updated the abstract and introduction to remove the term "Sybil-resistant aggregation" and replace it with the scoped claim.

---

## 3. Experiment Inconsistencies (Nine vs. Eleven; 201 vs. 495,671)

**Reviewer concern:** "The paper alternately reports nine and eleven experiments, and E6/E7 appear with conflicting numbers (e.g., 201 chains vs 495,671 chains; 6/6 tests vs 9,000 events). Please reconcile these inconsistencies."

**Response:** We have reconciled all numbers to match the actual codebase. The corrected experiment inventory is:

| ID | Name | Dataset | Metric |
|----|------|---------|--------|
| E1 | Chain integrity | 50 valid + 10 corrupt chains | 100% P/R |
| E2 | Status derivation | 2,204 exhaustive sequences | 2,204/2,204 correct |
| E3 | Snapshot round-trip | 38 concept files | 38/38 match |
| E4 | Precondition enforcement | 13 test cases | P=1.0, R=1.0, F1=1.0 |
| E5 | Multi-agent auditability | 5-agent simulation | 5/5 chains integrity OK |
| E6 | IBM AML pipeline | 201 accounts, 9,300 events | 201/201 integrity OK |
| E7 | Real-time pattern detection | 9,300 AML transactions | 6/6 tests, 0 FP on legit |
| E8 | Edge sync | 5 offline-merge tests | 5/5 zero conflicts |
| E9 | Git baseline | Per-event diagnostic | Semantic violation classification |
| E10 | FDE pipeline | 201 accounts | 201/201 validation pass |
| E11 | Side-effect stress | 1,000 effects | All succeed after retry |

The 495,671-account / 5.08M-event figure originated from a planned full-dataset evaluation that was never integrated into the repository. We have removed all claims of having evaluated at that scale and instead state it explicitly as **future work** (Section 6.5). The abstract, introduction, contributions, experiment design, results, discussion, and conclusion have all been updated.

---

## 4. Formal Definitions and Proofs (Theorems 1–4, Corollary 2)

**Reviewer concern:** "Formal definitions and proofs for the stated theorems are essential to assess technical soundness."

**Response:** We commit to adding an **anonymized appendix** (Appendix C) in the camera-ready version containing:

- Event alphabet Σ and typing function τ: Σ → EventType
- Well-formedness predicate WF(chain) ≡ verify_integrity(chain)
- Status derivation function δ: EventChain → DiscoveryStatus (recursive over event sequence)
- Confidence aggregation function γ: EventChain → [0,1] (bounded, monotonic, distinct-actor-limited)
- Fork/confluence semantics: event DAG, merge function μ, and proof that μ is associative, commutative, and idempotent over the CRDT semilattice
- Sketch proofs for Theorems 1–4 and the revised Corollary 2

The CRDT properties (commutativity, associativity, idempotence, monotonicity) are already validated by `tests/test_crdt_proofs.py`, which we will reference in the appendix.

---

## 5. Concurrent Edits, CRDTs, and Confluence

**Reviewer concern:** "How does the system handle concurrent edits and merges concretely today? Do you implement any CRDT or deterministic merge strategy across forks?"

**Response:** The current implementation (`adl_lite/crdt.py`) provides an operation-based CRDT state object (`CRDTState`) with a lattice merge that is:

- **Commutative**: `merge(a, b) == merge(b, a)` — verified in `test_crdt_proofs.py`
- **Associative**: `merge(merge(a, b), c) == merge(a, merge(b, c))` — verified
- **Idempotent**: `merge(a, a) == a` — verified
- **Monotonic**: state only advances in the status lattice — verified

The `SyncManager` (E8) uses this CRDT to merge offline event buffers deterministically. However, we acknowledge that adversarial testing (simulated conflicting writes, reorderings, replays) is not yet part of the suite. We have added this to the future-work list in Section 7 and will include it in the artifact's extended test suite.

---

## 6. Hardware and Environment Specifications for Throughput

**Reviewer concern:** "What are the hardware and software environments for the throughput experiments?"

**Response:** We have added `docs/experiments/HARDWARE_SPECS.md` documenting:

- **CPU**: Apple M3 Pro (12-core, 4.06 GHz performance cores)
- **RAM**: 36 GB LPDDR5
- **Disk**: 1 TB NVMe SSD
- **OS**: macOS 14.5
- **Python**: 3.12.12 (CPython)
- **Key libraries**: pydantic 2.7.4, networkx 3.3

E6 throughput: 31,100 events/s (9,300 events ÷ 0.299 s) on the above hardware. We have updated all throughput claims in the paper to reflect the actual 9,300-event dataset.

---

## 7. AML Pattern Detection Evaluation

**Reviewer concern:** "AML 'pattern detection' evaluation focuses on zero false positives on legitimate events; missing labeled suspicious cases and standard detection metrics make it difficult to interpret value."

**Response:** We agree that the current AML evaluation is a software-validation test, not a domain-efficacy benchmark. We have:

- Reframed E6/E7 in the paper as "pattern detection on synthetic + real data" rather than implying operational detection efficacy.
- Added a note that standard precision/recall/F1 against expert-annotated labels requires a multi-month interdisciplinary effort with financial-crimes experts and is beyond the scope of this systems contribution (Section 7, Future Work).
- The ground-truth "Is Laundering" flag in the IBM dataset is treated as a labeled positive for the purpose of computing standard metrics; we will add a `tests/test_aml_benchmark.py` to the artifact that computes precision, recall, F1, and ROC-AUC against this flag.

---

## 8. PROV-O, RDF-star, SHACL, and LD-Proofs

**Reviewer concern:** "Is there a fully functional PROV-O and RDF-star export in the artifact? Please provide example SPARQL queries and evidence of SHACL validation runs."

**Response:** The current artifact contains a basic Turtle string-builder in `tests/test_rdf_mapping.py` and hand-written LaTeX appendix examples. We acknowledge this gap and commit to the following for the camera-ready artifact:

- `adl_lite/prov_export.py`: Auto-generated PROV-O Turtle from `EventChain`
- `adl_lite/shacl_validation.py`: SHACL validation via `pyshacl` against the shapes in Appendix B
- `adl_lite/ld_proof.py`: Minimal Ed25519 signing sketch over canonical event JSON
- Example SPARQL queries over exported graphs (retrieving provenance, computing status)
- Updated appendices with `\lstinputlisting` of auto-generated output rather than hand-written examples

---

## 9. Float Normalization to Six Decimals

**Reviewer concern:** "What motivated six-decimal float normalization? How do you mitigate rounding-induced inconsistencies?"

**Response:** Six-decimal rounding was chosen because:

1. Confidence values in the current ontology are expressed in [0, 1], where 6 decimals (≈ 1 ppm resolution) is sufficient for all practical governance thresholds.
2. It eliminates hash divergence caused by platform-specific floating-point representations (IEEE 754 double-precision vs. extended precision).
3. It prevents JSON-library differences (e.g., `json.dumps` on CPython vs. other implementations) from producing different hashes for the same semantic value.

We have now **implemented** this normalization in `adl_lite/models.py` via `_round_floats(obj, ndigits=6)`, which recursively rounds floats in dicts and lists before hashing. All 350 existing tests pass after this change.

---

## 10. Anonymized Artifact with Reproduction Scripts

**Reviewer concern:** "For a Semantic Web audience, could you provide an anonymized artifact with scripts to reproduce exports, validation, and signing?"

**Response:** Yes. The artifact (to be submitted via Zenodo / Figshare with an anonymized GitHub repository) will include:

- `reproduce.sh`: Runs all 11 experiments and generates the results tables
- `reproduce_prov.sh`: Exports all example concepts to PROV-O Turtle and validates with `rdflib`
- `reproduce_shacl.sh`: Validates exported RDF against Appendix B SHACL shapes using `pyshacl`
- `reproduce_sign.sh`: Generates an ed25519 keypair, signs a sample event, and verifies the signature
- `requirements.txt` with pinned versions
- `HARDWARE_SPECS.md` for full reproducibility context

---

## Changes Checklist

| File | Lines | Change |
|------|-------|--------|
| `adl_lite/models.py` | +18, ~10 | Added `_round_floats()` helper; updated `_compute_hash()` docstring; timestamps preserved in hash; float normalization implemented |
| `docs/paper/PAPER_ESWC_ISWC_2027.md` | ~40 replacements | Abstract, intro, contributions, experiment design, results, discussion, conclusion: 9→11 experiments, 495k→201 accounts, Sybil claim downgraded, timestamp claims corrected |
| `docs/paper_v3/sections/abstract.tex` | ~1 replacement | Abstract: 9→11 experiments, corrected E6 scale, Sybil claim, timestamp claim |
| `docs/paper_v3/sections/01_introduction.tex` | ~1 replacement | Contribution 1: 495k→201 accounts |
| `docs/paper_v3/sections/03_architecture.tex` | ~9 replacements | Propositions 1 & 3 revised; timestamp exclusion→inclusion; Corollary 2 renamed; clock-skew section rewritten |
| `docs/paper_v3/sections/04_experiment_design.tex` | ~10 replacements | E6 dataset, resource util, phases, tables, chain-length distribution: 495k→201 |
| `docs/paper_v3/sections/05_results.tex` | ~8 replacements | Results tables, throughput, integrity claims: 495k→201 |
| `docs/paper_v3/sections/06_discussion.tex` | ~1 replacement | Discussion paragraph: 495k→201 |
| `docs/paper_v3/sections/07_conclusion.tex` | ~3 replacements | Conclusion: 9→11 experiments, 495k→201, throughput corrected |
| `docs/experiments/HARDWARE_SPECS.md` | new | CPU, RAM, disk, OS, Python version documented |
| `docs/paper/review_responses/RESPONSE_ROUND4.md` | new | This document |

---

## Final Note

We believe these changes directly address the reviewer's concerns while preserving the paper's core contributions: event-first operational semantics, deterministic state derivation, closed action registries, and lightweight deployment. The integrity of the hash chain is now accurately described (timestamps included), the experimental claims are reconciled with the codebase, and the Sybil claim is appropriately scoped. We look forward to the reviewer's assessment of this revision.
