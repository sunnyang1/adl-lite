# Changelog

All notable changes to ADL Lite are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0-alpha] — 2026-06-25

### Added

- **Phase 2 Slice-2 — tenant quota enforcement (R12)**:
  - `adl_lite/quota.py` (new): `QuotaPolicy` (`max_api_calls` / `max_entities` / `period`),
    thread-safe `QuotaConfig` singleton, `check_quota` FastAPI dependency that raises
    `HTTPException(429)` when a tenant exceeds its limit (response body carries `detail`,
    `quota`, `current`, `retry_after`; a standard `Retry-After` header is also set), and
    `configure_quota`.
  - `adl_lite/api.py`: `meter_api_call` now depends on `check_quota` and records usage under
    the tenant's configured `period` (daily / monthly); the usage and export endpoints are also
    gated by `check_quota`; `create_app` gains `quota_max_api_calls` / `quota_max_entities` /
    `quota_period`.
  - `adl_lite/config.py`: `get_api_config` reads `QUOTA_MAX_API_CALLS` / `QUOTA_MAX_ENTITIES` /
    `QUOTA_PERIOD`.
  - `adl_lite/metering.py`: `record_api_call` / `record_entity` accept a `period` argument so
    daily and monthly quotas align with the recorded window (previously daily quotas never
    fired because usage was always recorded under the monthly window).
  - Default behaviour (no quota configured) is unlimited, so single-tenant deployments see
    zero regression.

- **Phase 5 formal-methods extension**:
  - TLA+ bounded checking now covers CRDT merge and consensus/multi-agent
    transitions in addition to the original single-chain spec:
    - `specs/CRDTMerge.tla` models two concurrent branches sharing a genesis,
      with invariants for commutativity, associativity, idempotence, and
      status/confidence preservation (Theorem 9).
    - `specs/ConsensusEngine.tla` models multi-agent appends governed by the
      ontology lifecycle graph and an `N_min` distinct-validator guard
      (Theorems 6/8).
  - `scripts/run_tlc.py` extended with `--spec`, `--n-min`, and `--workers`
    flags; it generates per-spec `MC.cfg` files and skips gracefully when TLC
    is not installed.
  - `tests/test_run_tlc.py` covers config generation, argument parsing, and
    missing-TLC handling.
  - Buildable Coq/Iris skeleton under `formal/coq/`:
    - Core theories `Status.v`, `Event.v`, `Confidence.v`, `Chain.v`,
      `Invariants.v`, and `CRDT.v` formalise the status lattice, event model,
      confidence boundedness, well-formedness preservation (Theorem 7), and
      branch-merge CRDT properties (Theorem 9).
    - Optional Iris stubs `event_chain_ra.v` and `concurrent_append.v` set up
      a resource-algebra placeholder and a Hoare-triple stub for split-lock
      append.
    - Build files: `_CoqProject`, `Makefile`, `dune-project`, `adl_lite.opam`,
      and per-theory `dune` files.
  - `docs/verification_status.md` and `docs/experiments/tlc_status.md` updated
    to reflect the new specs and Coq skeleton.

### Changed

- Phase 5 formal skeletons advanced from stubs to closed proof scripts:
  - `formal/coq/theories/CRDT.v` is now a fully closed Coq proof of
    Theorem 9: all helper lemmas (`sort_nat_sorted`,
    `sort_by_id_preserves_ids`, `dedup_preserves_ids`,
    `merge_branch_eq_events_same_id` and its assoc/idem variants,
    `all_events_valid_merge`, `distinct_ids_merge`,
    `increasing_ids_merge`, and `all_same_id_equal_in_union3`) are
    now `Qed`, leaving no `Admitted` lemmas in the file.
  - `formal/coq/iris/concurrent_append.v` now proves the real Iris
    ghost-state update for split-lock append.

## [0.4.2-alpha] — 2026-06-24

### Added

- **Phase 4 vector index + LLM normalization**:
  - Pluggable embedding backends in `adl_lite/embeddings.py`
    (`SentenceTransformerBackend`, `OpenAIBackend`) with local-first defaults.
  - FAISS-backed persisted vector index in `adl_lite/vector_index.py`
    (`VectorIndex`) with add/update/delete/search, pre-filtering, save/load,
    SQLite metadata backup, and thread-safe RLock access.
  - LLM-driven canonicalization in `adl_lite/canonicalization.py`
    (`CanonicalizationEngine`, `OpenAILLMBackend`) that clusters near-duplicates,
    proposes canonical forms, and emits auditable ADL action blocks; dry-run by
    default.
  - Semantic search integration in `ADLMemory` using optional `VectorIndex`.
  - New CLI subcommand `adl-lite normalize` for dry-run or executed LLM
    normalization.
  - New experiments `E29` (Vector Index Recall) and `E30` (LLM Normalization).

### Changed

- `near_duplicate.py` now extracts rich text (`_extract_embedding_text`) for
  embedding comparison while keeping name-only text for Jaccard/Levenshtein.

## [0.4.1-alpha] — 2026-06-23

### Added

- **Phase 3 scale architecture**:
  - `EventChain` split-lock design (`_events_lock` + `_cache_lock`) to reduce
    contention under high concurrency.
  - Incremental `verify_integrity()` caches the verified prefix and only
    validates newly appended events in the common append path.
  - zstd+msgpack compressed cold storage in `adl_lite/cold_storage.py`
    (`archive(..., compressed=True)`), with streaming decompression and a clear
    error message when scale extras are missing.
  - `ADLMemory` cold-tier integration with auto-archival:
    `cold_threshold` triggers compressed archival of large chains during
    `store_with_events()`; `retrieve_chain()` reconstructs the full chain from
    Warm + Cold tiers.
  - New scale experiments `E27` (1M event scale) and `E28` (10k concurrent
    agents).

## [0.4.0-alpha] — 2026-06-22

### Breaking Changes

- **`resolve_did_key()` now returns `DIDDocument` instead of `Ed25519PublicKey`.**
  This aligns all DID methods behind a normalized document abstraction. Callers
  that need the raw Ed25519 key should use `doc.key_for_purpose()` or the
  internal helper `_ed25519_public_key_from_doc()`.

### Added

- **Runtime SHACL governance** (`adl_lite/shacl_validation.py`):
  - `validate_adl_document(doc)` runs built-in SHACL shapes directly on an
    `ADLDocument`, including Concept, Event, Agent, Relation, and CalibrateEvent
    shapes.
  - Relation shape enforces source/target presence, predicate, and confidence
    bounds.
  - CalibrateEvent shape enforces `observedAccuracy ∈ [0, 1]`.

- **Auto domain-expert calibration** (`adl_lite/calibration.py`):
  - `MARGINCalibrator.update_accuracy_ewma()` smooths new observations.
  - `apply_calibration_event()` consumes `CALIBRATE` events.
  - `update_from_feedback()` derives observed accuracy from predicted confidence
    and ground truth.
  - Built-in `CalibrationSideEffect` in `ActionExecutor` wires the `calibrate`
    action to the calibrator.

- **Relation governance closed loop** (`adl_lite/relation_validator.py`,
  `adl_lite/validator.py`):
  - `ADLValidator` now calls `RelationValidator` for Invariant 2 lifecycle
    checks on every document.
  - Strict mode adds predicate-semantic checks: required/allowed `mapping_type`,
    no self-referential transitive/symmetric relations.
  - Optional `status_resolver` callback for validating external relation
    endpoints.

- **Dynamic collusion resistance** (`adl_lite/ontology.py`,
  `adl_lite/action_executor.py`, `adl_lite/consensus.py`):
  - `OntologyManager.min_distinct_validators()` reads
    `collusion_resistance.min_distinct_validators` from the ontology YAML.
  - `ActionExecutor` and `ConsensusEngine` enforce the dynamic minimum when
    processing `VALIDATE` transitions.

- **Multi-method DID resolver** (`adl_lite/did_resolver.py`):
  - `DIDResolver` dispatcher supporting `did:key`, `did:web`, and `did:ethr`.
  - `did:web` resolution over HTTPS with support for JWK, multibase, base58, and
    hex public-key encodings.
  - `did:ethr` resolution and signature verification via `ecrecover`
    (requires optional `[did]` extras: `web3`, `eth-account`, `coincurve`).
  - Public API additions: `resolve_did`, `resolve_did_web`, `DIDDocument`,
    `VerificationMethod`.

- **Linked Data Proofs** (`adl_lite/ld_proof.py`):
  - `Event.proof` field for W3C Data Integrity style proofs.
  - `create_event_proof()` generates `Ed25519Signature2020` proofs tied to a DID
    `verificationMethod`.
  - `verify_event_proof()` verifies proofs against `did:key`, `did:web`, and
    `did:ethr` during `EventChain.verify_integrity()`.
  - Legacy `sign_event()` / `verify_event_signature()` API preserved.

- **Merkle batch verification** (`adl_lite/merkle.py`):
  - `MerkleTree` with SHA-256, inclusion proofs, and serialization.
  - `TransparencyAnchor` now supports Merkle root anchors
    (`anchor(..., use_merkle=True)`), per-chain inclusion proofs, and
    verification.
  - CLI additions: `adl-lite anchor --merkle --proofs-dir <dir>` and
    `adl-lite verify-inclusion <adl_id> --proof <json>`.

- **TLA+ formal specification skeleton** (`specs/EventChain.tla`):
  - Models EventChain state, lifecycle LUB, G-Counter confidence, and
    well-formedness invariants.
  - `scripts/run_tlc.py` wrapper for bounded TLC model checking.
  - `docs/paper_ao/supplementary/appendix_i_tla.tex` updated to reference the
    real spec.

- **New optional extras** in `pyproject.toml`:
  - `[did]` — Ethereum / secp256k1 dependencies.
  - `[gov]` — SHACL / RDFLib dependencies (preparation for Phase 2).
  - `[scale]` — FAISS, zstd, msgpack (preparation for Phase 3).

### Changed

- `KeyRegistry.get_public_key()` now resolves `did:key` through the new
  `DIDDocument` abstraction.

### Fixed

- `EventChain._lock` switched from `threading.Lock()` to `threading.RLock()` to
  avoid a macOS deadlock when `cryptography` (OpenSSL) and `torch` /
  `sentence-transformers` (OpenMP) are loaded in the same process.
- `did:web` DID document parsing now percent-decodes method-specific IDs and
  robustly handles base64url padding.

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
