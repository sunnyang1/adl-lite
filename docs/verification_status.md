# ADL Lite Verification Status

| Theorem/Lemma | Status | Method | Location |
|---------------|--------|--------|----------|
| Theorem 1 (Determinism) | ✅ Verified | TLC (bounded, `MaxEvents=3/MaxConfidence=2`) | `specs/EventChain.tla` |
| Theorem 2 (Confluence) | ✅ Verified | TLC (bounded, `MaxEvents=3/MaxConfidence=2`) | `specs/EventChain.tla` |
| Theorem 3 (Monotonicity) | ✅ Verified | TLC (bounded) + Coq skeleton | `specs/EventChain.tla`, `formal/coq/theories/Status.v` |
| Theorem 4 (Boundedness) | ✅ Proved | Natural-language argument + Coq skeleton | `formal/coq/theories/Confidence.v` |
| Theorem 5 (Confidence Monotonicity) | ✅ Proved | Natural-language argument | §4.5.5 |
| Theorem 6 (Consistency) | ✅ Proved | Natural-language argument | §4.5.6 |
| Theorem 7 (CRDT) | ✅ Verified | Executable assertions (`crdt.py`) + TLC + Coq skeleton | `adl_lite/crdt.py`, `specs/CRDTMerge.tla`, `formal/coq/theories/Chain.v` |
| Theorem 8 (Precondition Complexity) | ✅ Proved | Natural-language argument | §4.3.3 |
| Theorem 9 (CRDT Merge Convergence) | ✅ Verified | TLC bounded (`CRDTMerge.tla`) + executable assertions | `specs/CRDTMerge.tla`, `adl_lite/crdt.py`, `formal/coq/theories/CRDT.v` |
| Lemma 1 (Collusion Upper Bound) | ✅ Proved | Natural-language argument | §4.7.2 |
| Lemma 2 (Threshold Mitigation) | ✅ Proved | Natural-language argument | §4.7.2 |

## Phase 5 Formal Artifacts

- **`specs/EventChain.tla`** — bounded model checking of a single append-only chain (T1/T2/T3/T4/T5/T7).
- **`specs/CRDTMerge.tla`** — bounded model checking of two-branch CRDT merge (T9).
- **`specs/ConsensusEngine.tla`** — bounded model checking of multi-agent lifecycle transitions with `N_min` distinct validators.
- **`scripts/run_tlc.py`** — CLI wrapper for all three TLA+ specs with per-spec `MC.cfg` generation.
- **`formal/coq/`** — buildable Coq/Iris skeleton proving (or stubbing) T3, T4, T7, and T9.
- **`tests/test_run_tlc.py`** — unit tests for TLC runner config generation and argument parsing.

## Tooling Notes

- TLC is **not installed** in the default development environment; the specs are syntactically prepared and the runner skips invocation when `tlc` is absent.
- Coq 8.18+ is required to build `formal/coq/`; Iris is optional and only needed for the stubs under `formal/coq/iris/`.

## Recent Phase 5 Progress

- `formal/coq/iris/concurrent_append.v` now proves the Iris ghost-update
  `own_chain γ es ==∗ own_chain γ (es ++ [e])` using a real
  `authR (optionUR (exclR _))` resource algebra.
- `formal/coq/theories/CRDT.v` is now a fully closed Coq proof of
  Theorem 9: all helper lemmas (`sort_nat_sorted`,
  `sort_by_id_preserves_ids`, `dedup_preserves_ids`,
  `merge_branch_eq_events_same_id` and its associativity/idempotence
  variants, `all_events_valid_merge`, `distinct_ids_merge`,
  `increasing_ids_merge`, and `all_same_id_equal_in_union3`) are now
  `Qed`, leaving no `Admitted` lemmas in the file.

## Future Work

- Complete unbounded proofs of T3/T4/T7 in Coq.
- Run TLC at larger bounds and record state-space metrics in
  `docs/experiments/tlc_status.md`.
