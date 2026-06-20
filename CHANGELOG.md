# Changelog

All notable changes to ADL Lite are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.5] — 2025-06-20

### Breaking Changes

- **CRDT semantics migration (LWW → LUB/G-Counter).**
  `EventChain.status` now derives via a **join-semilattice LUB** over the lifecycle
  lattice (`provisional < forked < validated < deprecated < archived`) instead of
  the previous last-write-wins (LWW) rule. Once a concept reaches a higher-status
  state, it **never regresses**.
  - `DEPRECATE` after `VALIDATE` → `deprecated` (permanent)
  - `ARCHIVE` after any state → `archived` (permanent)
  - `REGISTER` after `DEPRECATE` → `deprecated` (not `provisional`)
  - `FORK` after `VALIDATED` → parent stays `validated` (not `forked`)

- **`EventChain.confidence` now uses G-Counter (max) semantics.**
  Confidence is the **maximum** over all `VALIDATE` / `SNAPSHOT` events, not the
  most recent one. Once a high-confidence validation is recorded, subsequent
  lower-confidence assertions **cannot decrease** the aggregate.
  - `VALIDATE(0.9)` → `VALIDATE(0.5)` → confidence stays `0.9`
  - This prevents malicious or erroneous validators from downgrading a concept.

### Added

- **Incremental CRDT caches** in `EventChain`:
  - `_cached_status` and `_cached_status_order`: updated on every `append()`,
    making `status` query O(1).
  - `_cached_confidence`: updated on every `append()`, making `confidence`
    query O(1).
  - Defensive fallback re-computation when `_events` is mutated directly
    (bypassing `append()`).

- **`StatusOrder` (IntEnum)** in `crdt.py`: unified lattice order for status
  derivation, used by both `CRDTState` and `EventChain`.

- **E25 microbenchmark experiment** (`experiments/e25_microbenchmark.py`):
  - Precondition evaluation time vs rule count `k`
  - Confidence aggregation time (`γ_default`, `γ_agg`, `γ_cal`) vs validator
    count `|V|`
  - Storage overhead comparison (ADL Lite / Git / PROV-O)

- **`examples/weather_data_retrieval.md`**: end-to-end multi-agent lifecycle
  case study demonstrating registration → validation → dispute → fork →
  deprecation → downstream consumption.

- **6 new CRDT semantics tests** (`tests/test_crdt_proofs.py`):
  - `test_confidence_g_counter_max`
  - `test_status_lub_deprecated_dominates_validate`
  - `test_status_lub_archived_dominates_all`
  - `test_confidence_max_with_snapshot`
  - `test_status_provisional_by_default`
  - `test_confidence_zero_with_no_validate`

### Changed

- **Paper §4.5**: `δ(C)` formula updated from LWW (`f(τ_last)`) to LUB
  (`max_{≺}{f(e.τ)}`).
- **Paper §4.5**: `γ_default` updated from `e_last(V)` to G-Counter `max`.
- **Paper Table 2**: lifecycle transition matrix updated for CRDT precondition
  semantics.
- **Paper §4.7**: CRDT migration described as "completed" (Phase 1 & 2), with
  Phase 3 (semantic merge policies) as future work.
- **Paper §6.2 L8**: PROV-O provenance mapping and JSON-LD serialization now
  listed as **implemented** (only SHACL remains future work).
- **Paper §6.2 L12**: fork resolution described as migrated to CRDT LUB in
  v0.3.5 (not LWW).

### Fixed

- **Paper–code consistency**: all "last-VALIDATE" and "LWW" references in the
  paper aligned with the CRDT code implementation.

---

## [0.3.0] — 2025-06-15

### Added

- Peer review round 4: AgentHub, Zhou G1-G3, DIDs/VCs citations.
- Precondition formal language (`eval(r, C)`) with `apply(κ, lookup(f, C), v)`.
- PROV-O mapping table with loss analysis.
- REVOKE semantics discussion (epistemic weakening vs. cessation).
- Multi-agent weather-data-retrieval case study in paper §5.
- γ ablation microbenchmark (E25) in paper §5.
- LWW → CRDT migration path (Phase 1/2/3) in paper §4.

### Fixed

- Theorem 7/9 numbering.
- E6b table data.
- Appendix E Theorem 7 proof.

---

## [0.2.0] — 2025-05-30

### Added

- Initial release with 590 tests.
- Four-layer document model (L1/L2/L3/L4).
- EventChain with cryptographic integrity.
- ActionExecutor with precondition language.
- ConsensusEngine with fork/merge.
- Calibration layer (γ_default, γ_agg, γ_cal).
- CRDT convergence proofs (Theorem 9).
- OWL 2 DL / RDF-star / JSON-LD export.
- 13+ experiments (E1–E23).
