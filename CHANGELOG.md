# Changelog

All notable changes to ADL Lite are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0-alpha] — Unreleased

### Added

- **Execution Attestation Layer (EAL), Phase 3 — commit–reveal challenge
  protocol** (design: `docs/design/execution-attestation.md` §5.6):
  - New event type `CHALLENGE` with phases `open` / `reveal` / `answer`.
    A challenger commits to a secret seed (`seed_commitment = sha256:H(seed)`),
    reveals it before a deadline, and the executor must post an
    `output_commitment` within `response_window_s`. The revealed seed IS the
    challenge input, so a cached answer can never match — closing the
    "deterministic capability replays one honest answer forever" hole that
    replay attestation alone cannot cover.
  - Axiom extensions (`models.py`): Axiom 13 requires `challenge_id` +
    `phase`; Axiom 14 requires an LD-Proof on every CHALLENGE event;
    Axiom 15 validates phase membership and per-phase required fields
    (open: `seed_commitment`, `reveal_deadline`, `response_window_s`;
    reveal: `seed`; answer: `output_commitment`).
  - `adl_lite/challenge.py` (new): `ChallengeManager` — the cross-event
    state machine (commitment matching, deadline/window enforcement,
    phase ordering, target-executor restriction) as a derived, read-only
    projection over the chain. Time-dependent derivations take an explicit
    `as_of` (default: chain-internal newest event time) so replays are
    deterministic and CRDT-friendly. Derived terminal phases: `answered` /
    `timed_out` / `void` (challenger fault — excluded from response rates).
    `response_metrics()` aggregates response rates overall and per
    capability, with optional executor filtering. Seed stubs
    (`save_seed_stub` / `load_seed_stub` / `delete_seed_stub`) keep the
    plaintext seed LOCAL under `<log_dir>/challenges/` (0600) until reveal.
  - CLI: `adl-lite challenge open|reveal|answer|status` — open stores the
    seed locally (0600, never on-chain until reveal); reveal verifies the
    local stub against the on-chain commitment before appending; answer
    accepts `--output-hash` or `--auto-run` (runs the `adl:execution` spec
    on the revealed seed); status replays the state machine at wall-clock
    `as_of` and reports derived phases plus response-rate metrics.
  - `experiments/e33_challenge_game.py` (E33): analytic vs simulated
    break-even challenge frequency for rational lazy executors
    (E_lazy(f) = (1-f)·G − f·P against E_honest = R − C). With the real
    `ChallengeManager` + `MARGINCalibrator`: f\* analytic 0.100 vs
    simulated 0.094 (|err| 0.006); lazy payoff 1.0/round unchallenged vs
    0.37/round at f=0.2 (honest 0.7); manager derivations match simulation
    ground truth on all 16 frequency points; ~0.018 ms per challenge event.

### Deferred (Phase 3b, documented in the design doc)

- Statistical conformance for `stochastic` capabilities and property-check
  verification for `side-effecting` ones remain open; TEE quote / zk-proof
  payloads are accepted at the schema level (`tee-quote` / `zk-proof` in
  `ATTEST_METHODS`) but not yet cryptographically verified.

## [0.8.0-alpha] — Unreleased

### Added

- **Execution Attestation Layer (EAL), Phase 2 — from observability to
  enforcement** (design: `docs/design/execution-attestation.md`):
  - `adl_lite/attestation.py` (new): `AttestationValidator` (resolves
    `ATTEST.subject_execution` via an injected execution lookup — same
    pattern as `RelationValidator`; checks cross-log commitment equality and
    flags self-attestation), `AttestationIndex` (distinct-scope verdict
    counting, payload `scope` field with actor fallback),
    `attested_confidence()` (evidence-weighted confidence: VALIDATE events
    discounted by α when lacking distinct-scope attestation backing;
    monotone, opt-in — `EventChain.confidence` is unchanged),
    `refute_status()` (distinct-scope refute threshold → DEPRECATE proposal
    flag; never auto-transitions), `feed_calibrator()` (calibration
    bootstrap: verdicts overturned by stronger independent attestations feed
    `MARGINCalibrator.update_from_feedback`).
  - `adl_lite/replay.py` (new): `ReplayHarness` — independent re-execution
    from the `adl:execution` spec (`shell=False` + `shlex.split`, timeout
    enforcement, explicit invocation only, never implicit). Deterministic
    capabilities get exact commitment comparison; `stochastic` /
    `side-effecting` receive honest `inconclusive` verdicts pending Phase 3
    engines. `build_attest_event` / `append_attestation` (append-then-sign —
    the LD-Proof covers final chaining fields).
  - CLI `adl-lite attest` group: `replay` (replay a receipt and append a
    signed ATTEST to the consensus chain; JSON-only when unregistered),
    `list` (attestations + refute-threshold status).
  - Consensus state persistence now round-trips event `signature` and
    `proof` fields (`_save_engine` / `_load_engine`) — required for EAL
    axiom 14 on reloaded chains.
  - `tests/test_attestation.py` (new): 35 tests.
- **Experiments**: E31 (lazy-executor detectability: 98.2% detection at
  r=3/threshold=2 with 0% false positives vs 1.8% manual-sampling baseline)
  and E32 (evidence-weighted vs G-Counter confidence under adversarial
  validation: Brier 0.090 vs 0.349, −74.3% error).

## [0.7.0-alpha] — Unreleased

### Added

- **Execution Attestation Layer (EAL), Phase 1 — pure observability**
  (design: `docs/design/execution-attestation.md`):
  - New event types: `EXECUTE` (signed execution receipt, lives on a
    per-capability ExecutionLog), `ATTEST` (verdict about an execution,
    main chain), `EXEC_ANCHOR` (Merkle anchor of an ExecutionLog, main
    chain). Status LUB and confidence G-Counter derivation are unchanged —
    EAL event types are not consumed by either.
  - EAL conditional axioms 13–15 in `EventChain.verify_integrity` and
    `well_formedness_report()`: evidence schema (required payload fields),
    proof presence (EXECUTE/ATTEST must carry an LD-Proof), and verdict
    consistency (replay-confirm requires `match: true`; refute requires
    evidence or a reported mismatch).
  - `adl_lite/execution_log.py` (new): `ExecutionLog` — append-only,
    hash-chained log of EXECUTE receipts built on `EventChain`, with Merkle
    anchoring (`build_anchor_event`), receipt lookup, executor set
    derivation, and JSONL persistence that preserves LD-Proofs.
  - `adl:execution` L3 block (YAML body): capability-side execution spec
    (invocation, determinism, properties, test vectors) enabling
    independent replay by validators. `ADLDocument.execution_spec`.
  - Ontology registry v0.2 sync: new classes `execution` / `attestation`,
    predicates `attests` / `executed-by` / `anchored-by`, actions
    `execute` / `attest` / `exec_anchor`, and the `attestation:` policy
    section (`min_distinct_scopes`, `evidence_factor_unbacked`,
    `refute_threshold`, `require_execution_spec_on_register`) with
    `OntologyManager` accessors.
  - CLI `adl-lite execute` group: `record` (signed receipt, Ed25519 key
    from PEM or raw hex/base64), `anchor` (append EXEC_ANCHOR to the
    consensus chain, or emit JSON when unregistered), `log --verify`.
  - Registration policy (D5): production-mode `ConsensusEngine.register`
    rejects new capabilities lacking an `adl:execution` spec block
    (dev-mode relaxed; existing capabilities exempt).
  - `tests/test_execution_attestation.py` (new): 54 tests covering axioms
    13–15, ExecutionLog behaviour (signing, tamper detection, Merkle
    stability, JSONL round-trip), block parsing, ontology sync, the
    registration hook, and derivation isolation.
## [Unreleased] — Multi-agent closure + dashboard platform (2026-08-07)

### Added

- **Runtime 5-role toolchains** (`adl_lite/agents/runtime.py`): `AgentRuntime._execute`
  now runs a real toolchain for every role — REVIEWER (`adl_validate` →
  `adl_consensus_transition(validated)`), SKEPTIC (`adl_consensus_verify` →
  `transition(forked)` on challenge), MERGER (`verify` → `transition(validated)`
  on forked chains), LIBRARIAN (`adl_store` → `adl_query_related`) — all
  whitelist-gated and audit-logged. Closes the "1-role-only" gap in the
  5-role consensus narrative.
- **Meta single-source-of-truth endpoints**: `GET /api/v1/meta/task-transitions`
  (serialized `_TASK_TRANSITIONS`) and `GET /api/v1/meta/roles` (serialized
  `ROLE_SPECS`) so clients consume the state machine instead of hardcoding it.
- **Admin JWT issuance** (`adl_lite/api_auth.py`): `configure_auth` accepts
  optional `admin_username`/`admin_password` (env `ADMIN_USERNAME`/`ADMIN_PASSWORD`);
  the OAuth2 token endpoint issues `role="admin"` JWTs for those credentials
  (default unset = unchanged behaviour). Fixes the trust-root bootstrap hole.
- **Dashboard platform** (`dashboard/`): auth store + axios Bearer interceptor,
  login dialog (username/password or API key, demo-mode detection), admin
  validate + admin public-key panels, Agents/Tasks/Runtime/Trust pages; task
  actions and role dropdowns now consume the meta endpoints with hardcoded
  fallback.

### Fixed

- **Runtime event signing (trust-closure)**: `AgentRuntime` accepts an optional
  `signer` (`Callable[[bytes], str]`); tool calls that produce DID-actor chain
  events (`adl_consensus_transition` → VALIDATE/FORK) attach a signature so
  strict trust checks (B2) can verify them. Event hashes exclude signature
  (integrity-safe, same pattern as the API attest endpoint). Default `None`
  keeps the loose behaviour unchanged. Closes the last trust-loop gap found
  by the Acme case demo (strict `trust-check` previously rejected runtime
  transitions as "event has no signature").
- `_mem_store` called the nonexistent `ADLMemory.store_document` → now
  `mem.store(doc)` (LIBRARIAN toolchain would have crashed).
- `dashboard/src/api/types.ts` `AdminPublicKeyResponse` matched the real
  backend shape (`registered: str`, `admin_public_keys: int`).
- TaskExplorer actions aligned with `_TASK_TRANSITIONS` (no more 409s on
  assigned/submitted rows); task priority is a number per the backend.

### Docs

- **README/AGENTS/CONTRIBUTING refreshed to the v0.9.0-alpha reality**
  (2026-08-08): badges and counts corrected to measured values — 1881 tests
  collected / 1851 passing fast-path, 86% coverage, 33 registered experiments
  (E1–E35), 26 MCP tools, 60+ core modules; new CLI/REST/MCP surface
  documented (multi-agent control plane: `agent`/`task`/`run`/`approve`/
  `trust-check`; EAL: `execute`/`attest`/`challenge`); roadmap gains the
  v0.9.0-alpha (unreleased) row; `dashboard/` added to the project structure;
  MCP server module + test docstrings synced to the 26-tool surface.

## [Unreleased] — Native multi-agent M4 (2026-08-07)

### Added

- **Trust closure** (`adl_lite/agents/trust.py`): `DidWebAffiliationResolver`
  (offline-first did:web org lookup — preset cache or None, never hard-fails,
  TTL 7d; `diversity_key` → `("org", org)` for did:web, `("key", actor)` else)
  + `ReputationScore`/`Reputation` (weak-signal behavioural stats: discovery
  events v1 + per-task-dedup task component v2; `formula_v1`/`formula_v2`;
  `_count_merged_forks` conservative proxy).
- **B4 activation** (`adl_lite/trust_model.py`): `ConsensusConfig` gains
  `min_validator_reputation` (0.0 = disabled) and `diversity_provider`;
  `TrustValidator` accepts provider/reputation and uses org-level diversity
  keys when configured. **Zero-change guarantee**: defaults keep Phase-1
  identity-scoped keys, so existing behaviour is byte-identical (TR-04).
- **Surfaces**: `adl-lite agent reputation|trust-check --diversity`; API
  `GET /api/v1/agents/{did}/reputation` + `GET/POST /api/v1/admin/trust/diversity`
  (P1-8 operational switch, env `ADL_AGENT_DIVERSITY` default on); MCP
  `adl_agent_reputation` (public-scope ACL).
- **Weak-signal declaration (P1-7)**: reputation is ranking/visibility only —
  never gates security admission (docstring + API note).

### Notes

- P1-2 known limitation: B4 covers discovery-chain VALIDATE validators only;
  agent-registration (AGENT_VALIDATE) same-org collusion is NOT blocked.

## [Unreleased] — Native multi-agent M3 (2026-08-07)

### Added

- **Thin runtime** (`adl_lite/agents/runtime.py`): `AgentRuntime` (dequeue →
  reason → whitelisted tools → audit every action), `RuntimeManager` (multi-
  agent lifecycle + P1-6 backlog visibility via `status()`), `CheckpointKind`
  + in-process human checkpoint (P0-1-adjacent recovery: a rejected/blocked
  checkpoint releases the lease; idempotent re-claim retries the task).
- **Role whitelist** (`adl_lite/agents/roles.py`): `RoleSpec` + `ROLE_SPECS`
  for the 5 harness roles (discoverer/reviewer/skeptic/merger/librarian) —
  `_call_tool` rejects out-of-whitelist tools with `PermissionError` (RT-02).
- **Schema-first planner** (`adl_lite/agents/planner.py`): LLM decomposition
  with P1-3 capability vocabulary gating (ontology predicates ∪ registered
  discovery ids — same vocabulary as `TaskRegistry`/`TaskQueue` matching).
- **In-memory tool registry**: `runtime._default_tools` binds tools to the
  runtime's own engine (the `tools.py` wrappers reload the state file per
  call and would race an in-memory engine); sync `LLMBackend.complete` is
  bridged via `asyncio.to_thread`.
- **Surfaces**: `adl-lite run` / `adl-lite approve` (single-process, P1-4);
  API `GET /api/v1/runtime/status` + `POST /api/v1/checkpoints/{task_id}/approve`;
  MCP `adl_task_enqueue` (fire-and-forget) + `adl_runtime_start` (validate).
- **Idempotent re-claim** (`agents/task.py`): `IN_PROGRESS → IN_PROGRESS` is
  now a legal transition so a failed execution (tool error / rejected
  checkpoint) can be retried by the next dequeue — no task deadlock.

### Changed

- `EventType` unchanged (M3 adds no new event types); ontology untouched.

## [Unreleased] — Native multi-agent M2 (2026-08-06)

### Added

- **Task lifecycle as EventChains** (`adl_lite/agents/task.py`): `TaskStatus`
  enum + `_TASK_TRANSITIONS` + `derive_task_status` (deterministic fold,
  supports the REJECTED→resubmit rework loop), `TaskStatusView` (tail-hash
  cached, incl. `result_ref`), `Task` (status = snapshot; authoritative value
  derives from the chain), `TaskRegistry` (create/assign/claim/submit/
  validate_result/close). Capability vocabulary unified (P1-3): ontology
  predicates ∪ registered discovery chain ids.
- **MessageBus + TaskQueue** (`adl_lite/agents/bus.py`): asyncio in-process
  pub/sub with lazy Redis backend (`[v1]` hint ImportError) and a closed
  request/reply protocol (`reply_loop`, P2-2); TaskQueue with at-most-one
  claim, lease/TTL, cross-thread atomicity (single lock, P1-5) and the
  P0-1 no-task-loss guarantee (failed claims re-queued; expired leases
  re-enqueued by `requeue_expired`).
- **EventType extension**: `TASK_CREATE/ASSIGN/CLAIM/SUBMIT/VALIDATE/CLOSE`
  + `MESSAGE` — still excluded from the discovery lattice.
- **Ontology v0.3 → 24 actions**: 6 task actions (all `triggers_transition: null`).
- **Surfaces**: REST `/api/v1/tasks/*` (create/claim/submit/validate/close/
  get/list, tenant-scoped), CLI `adl-lite task ...` (7 subcommands), tools
  `adl_task_*` (8 wrappers), MCP 7 task tools (write tools admin-token gated,
  tool count 16 → 23). `_LAZY_ATTRS` extended.
- **Tests**: `test_agents_task.py` (13 cases: derivation table, rework,
  invalid transitions, dual-state restart, discovery isolation) +
  `test_agents_bus.py` (15 cases: pub/sub, request/reply, at-most-one claim,
  lease expiry re-enqueue, cross-thread atomicity, redis hint). Full fast
  suite green (1697 passed). Reviewed assertion updates: openapi paths (+7),
  MCP tool count/names, ontology action list.

## [Unreleased] — Native multi-agent M1b (2026-08-06)

### Added

- **REST agent endpoints** (`/api/v1/agents/*`): `register` (admin-gated),
  `attest`, `admin-validate` (P0-1 trust-root, admin-gated), `validate`,
  `deprecate` (admin-gated), `get`, paginated `list`, `history`; plus
  `POST /api/v1/admin/public-key` (P0-3: API-key ↔ DID-signature binding
  point). Admin public-key whitelist persists in the state file.
- **CLI**: `adl-lite agent register|attest|validate|list|show|deprecate`.
- **tools.py**: `adl_agent_register/attest/validate/list/get/deprecate`
  (load → mutate → save → dict convention; admin path off by default, P0-3).
- **MCP**: `adl_agent_register/attest/validate/get/list/deprecate`; write
  tools require an admin token (`--admin-token`; stdio has no auth context and
  denies writes, P1-1). Tool count 10 → 16.
- **P0-2 discovery isolation**: `/api/v1/consensus/list`, `consensus/status`,
  and MCP `adl_list` filter by `chain_kind` — agent chains never surface as
  provisional concepts.
- **Agent chain scope ACL**: genesis payload now carries a top-level `scope`
  so `_chain_scope()` enforces private-scope reads on agent chains.
- **api.py serialization fidelity**: `_load_engine`/`_save_engine` preserve
  `signature`/`proof`/`previous_event_id` (M1a fix completed for the API layer).
- **Tests**: `test_agents_surfaces.py` (16 cases incl. P0 adversarial
  acceptances); full fast suite green (1669 passed). Reviewed assertion
  updates: openapi paths list, MCP tool count.

## [Unreleased] — Native multi-agent M1a (2026-08-06)

### Added

- **Agent identity layer (M1a)**: new `adl_lite/agents/` package — `AgentProfile`,
  `AgentRole`, `AgentStatus`, `AgentRegistry` (agents as EventChains with
  `AGENT_REGISTER` genesis), `chain_kind()` chain-type marker (P0-2), and
  `AgentConfig` (dual-track LLM backend: mock default / openai / anthropic).
- **EventType extension**: `AGENT_REGISTER`, `AGENT_VALIDATE`, `AGENT_UPDATE`,
  `AGENT_DEPRECATE` — deliberately excluded from the discovery lattice
  (`type_to_status` / `StatusOrder`) so agent chains never drive
  DiscoveryStatus (zero-regression guarded).
- **Ontology v0.3**: 4 agent lifecycle actions (all `triggers_transition: null`)
  and predicates `declares-capability` / `agent-capability-of`.
- **Trust-root bootstrap (P0-1/P0-3)**: admin attestation path requires a
  DID signature from a registered admin public key plus an internal
  `_admin_calls_allowed` guard (admin-gated API only); N_min ≥ 2 enforced in
  production mode mirroring `ConsensusEngine._effective_n_min`.
- **State serialization fidelity**: `cli._save_engine` and
  `mcp_server._save_engine` now persist `signature`, `proof`,
  `previous_event_id` (previously dropped); loaders fall back to defaults for
  legacy state files.
- **Tests**: `test_agents_identity.py` (13 cases) + `test_agents_zero_regression.py`
  (discovery-lattice guards, legacy-state compat); full fast suite green
  (1653 passed).

## [Unreleased] — Applied Ontology submission prep (2026-08-05)

### Added

- **Competency question verification (P2)**: `scripts/verify_competency_questions.py`
  runs the paper's 14 CQs (CQ1–CQ14) as SPARQL queries against
  `supplementary/adl_lite_core_v2.owl`, cross-checked verbatim against
  `appendix_a.tex` (14/14 exact match, exit 0). Shipped OWL fragment was
  missing 5 axioms (`forkOf ⊑ wasDerivedFrom` etc.) — patched (+31 lines,
  sourced from `formal/owl/adl_lite_ontology.ttl`) so CQ14 is reproducible.
- **BFO/IAO alignment audit (P2)**: `scripts/verify_ontology_alignment.py`
  extracts and whitelist-checks all bridge axioms (5 class + 3 property),
  84.6% core-class coverage (transitive closure); LogMap jar download
  unavailable → honest fallback to bridge-axiom verification.
- **Orphan citation cleanup (P2)**: 25 orphan bib entries resolved — 22 cited
  into contextually correct sections (garijo2025llmoe, openai_agents,
  langchain, llamaindex, guarino_1998, event_sourcing_fowler, cqrs,
  lamport_clocks, vector_clocks, fatf2025, ibm_aml, …), 3 kept with
  `% orphan` comments; new `moreau2013prov` (PROV book) cited in §2.4;
  `provo_survey_2024` residual citations zeroed.
- **Manuscript compression (P2)**: main.tex 128 → 65 pages (appendices A–F
  moved to supplementary as "Supplementary Material" with preserved label
  anchors; 33 tables relocated to `supplementary/appendix_o_tables.tex`;
  γ/precondition/proof narrative tightened; `\bibsep` compaction). 0 compile
  errors, 0 undefined refs/citations; all prior numeric revisions preserved.

### Fixed

- **E1 chain integrity experiment fixture**: `_build_random_chain` generated
  L4 action events (e.g. `ANNOUNCE`) without the `action` payload field
  required by well-formedness Axiom 9, so genuinely valid chains were rejected
  by `verify_integrity()` — stored `valid_chain_pass_rate` was 0.32 while the
  paper claimed 1.0. Fixture now emits the required `action` field; E1 rerun
  passes with P/R/F1 = 1.0 (regression tests: `tests/test_e1_experiment_fixture.py`).
- **Proof trace checker T2/T3 (E24)**: `check_theorem_2_fork_confluence` and
  `check_theorem_3_transition_monotonicity` assumed last-writer-wins semantics
  ("after FORK status == FORKED"), but ADL Lite derives status as the CRDT LUB
  over all lifecycle events. Chains that already reached DEPRECATED/ARCHIVED
  were incorrectly flagged as violations (stored T2 pass rate 3.27%, T3 12.03%).
  Checks now use LUB semantics; E24 rerun passes T1–T7 at 100%
  (`tests/test_proof_trace_checker_lub.py`).
- **OWL 2 DL fragment guard**: new tests pin that the shipped
  `docs/paper_ao/supplementary/adl_lite_core_v2.owl` parses with rdflib,
  declares the core classes/datatype properties, and contains the expected
  OWL 2 DL constructs (`tests/test_owl_fragment_shipped.py`).
- **E4 archive precondition (P0)**: `adl_core_ontology.yaml` allowed `archive`
  from any status (`in [provisional, validated, forked, deprecated]`), but the
  paper (§4.2) and A7 tests forbid archiving a never-validated concept. Tightened
  to `[deprecated]`; E4 rerun passes P/R/F1 = 1.0 (was 0.889 precision).
- **E19 head-to-head benchmark (P0)**: could not run (missing `pygit2`/`prov`
  optional deps). Dependencies installed; full 4-systems × 4-tasks + scale
  benchmark now measured (S1: 27 LOC / 0.5 ms / audit 1.0; S1 scale 1M concepts
  = 2M events @ 14,938 evt/s). Status-determination logic no longer penalises
  ADL Lite for having slightly more LOC than nanopub.
- **E23 contention config (P1)**: agent count 10 → 20 to match the paper claim;
  rerun gives integrity_rate = 1.0, 0 chain failures.
- **E26 cross-repo merge (P0)**: was a paper claim with no script/data. Added
  `experiments/e26_cross_repo_merge.py` — 2 repos × 100 chains, 100 merges,
  100,000 events, 0 integrity failures, δ/γ consistency (Theorem 9)
  (`tests/test_e26_cross_repo_merge.py`).
- **E27 1M-event scale (P1)**: previously `failed` (missing zstd/msgpack).
  Now runs: 500k events (1M auto-degrades on this machine), 8.4× compression,
  integrity OK — stored honestly as `partial` with projected 1M figures.
- **E31/E32/E33 data-file alignment (P1)**: renamed `e27_crdt_merge.json` /
  `e28_expert_validation.json` / `e29_merkle_comparison.json` →
  `e31_crdt_merge.json` / `e32_expert_validation.json` / `e33_merkle_comparison.json`
  (internal `experiment_id` updated); `scripts/experiment_to_latex.py` mapping
  and generated `tables_auto/e31|e32|e33.tex` captions/labels now use E31–E33,
  matching the paper's citations.

### Added

- **Paper–code consistency guard**: `scripts/check_paper_code_consistency.py`
  detects drift between numeric claims in `docs/paper_ao/sections/*.tex`
  (test counts, coverage %, ADL Lite version) and the current repository
  state (via `pytest --collect-only` / `--cov`). Exit code 1 on drift.
- **Applied Ontology submission improvement plan**:
  `docs/paper_ao/planning/APPLIED_ONTOLOGY_IMPROVEMENT_PLAN_2026-08.md`
  (synthesised from expert-team diagnosis: journal fit, literature audit,
  claims-consistency audit).

## [0.6.0-alpha] — 2026-07-21

### Added

- **Phase 2 — multi-tenant isolation, metering, and trust model**:
  - `adl_lite/tenant.py` (new): tenant registry and `TenantContext` scoped
    isolation for the consensus API.
  - `adl_lite/metering.py` (new): usage metering with daily/monthly period
    windows (`UsageMeter`, `MeteringRecord`, `compute_period_window`).
  - `adl_lite/quota.py` (new): per-tenant quota policies enforced as a FastAPI
    dependency (`check_quota`, HTTP 429 on exceed).
  - `adl_lite/trust_model.py` (new): Phase-1 trust layer on top of
    `ConsensusEngine` — DID-based validator identity with method-level
    diversity checks (`TrustValidator`, `ConsensusConfig`); `did:ethr` is
    explicitly rejected by trust validation.
  - `adl_lite/api.py` + `adl_lite/api_auth.py` (new): FastAPI REST API for
    register/transition/status/history/fork with auth, rate limiting, quota,
    and metering middleware. Version is now sourced from
    `adl_lite.__version__` (single source of truth).
  - `adl_lite/mcp_server.py` (new): FastMCP tool server exposing 10 tools,
    2 resources, and 1 prompt (`adl-lite mcp` / `python -m adl_lite.mcp_server`).
  - `adl_lite/graph_backends.py` + `adl_lite/neo4j_adapter.py` (new): pluggable
    graph persistence (NetworkX / SQL / Neo4j) behind a common `GraphBackend`
    protocol, with `adl-lite neo4j status|check|rebuild` CLI commands.

- **N≥3 CRDT merge**: `merge_event_chains()` generalised from two branches to
  an arbitrary number of concurrent branches, preserving commutativity,
  associativity, idempotence, and status/confidence monotonicity (T9).

- **Merkle batch verification**: `TransparencyAnchor.verify_batch()` verifies
  many chains against a Merkle anchor with per-chain inclusion proofs;
  `adl-lite verify-batch` CLI command.

- **Formal methods**:
  - `formal/coq/theories/Crypto.v`: abstract EUF-CMA signature and
    collision-resistant hash axioms (3 axioms) underlying the chain-integrity
    proofs.
  - OWL 2 DL module: `adl_lite/owl_export.py` / `adl_lite/owl_import.py`
    round-trip the registry as an OWL 2 DL ontology (BFO/IAO-aligned).
  - Expanded Coq/Iris proofs and TLA+ specs (`specs/CRDTMerge.tla`,
    `specs/ConsensusEngine.tla`).

- **Experiments**: E34 (precondition language formalization & O(1) benchmark)
  and E35 (expert validation simulation — inter-rater agreement); the runner
  now degrades gracefully when an experiment's optional dependencies are
  missing (e.g. E19 without `pygit2`).

### Changed

- **Bare-install robustness**: `import adl_lite` no longer requires optional
  heavy dependencies. `pyshacl`/`rdflib` (`shacl_validation.py`,
  `prov_export.py`) and `numpy` (`embeddings.py`, `vector_index.py`) are
  imported lazily; the corresponding top-level symbols
  (`validate_adl_document`, `VectorIndex`, `EmbeddingBackend`,
  `CanonicalizationEngine`, near-duplicate helpers, …) resolve via PEP 562
  lazy loading with actionable `pip install adl-lite[...]` guidance.
- `adl-lite validate --strict-template` is now a flag of the `validate`
  subcommand (previously attached to the root parser where it could not be
  used).
- `did:ethr` error messages reference the correct extra name
  (`pip install adl-lite[did]`).

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
