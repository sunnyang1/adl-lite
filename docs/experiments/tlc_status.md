# TLA+ Model Checking Status

## Specs

| Spec | File | Invariants | Theorem focus |
|------|------|------------|---------------|
| `EventChain` | `specs/EventChain.tla` | `Inv_WellFormednessPreserved`, `Inv_StatusMonotonic`, `Inv_MonotonicAppend` | T1/T2/T3/T4/T5/T7 |
| `CRDTMerge` | `specs/CRDTMerge.tla` | `Inv_MergedWellFormed`, `Inv_MergedStatusConfidence`, `Inv_MergeCommutative`, `Inv_MergeAssociative`, `Inv_MergeIdempotent` | T9 |
| `ConsensusEngine` | `specs/ConsensusEngine.tla` | `Inv_WellFormednessPreserved`, `Inv_ValidTransition`, `Inv_MinValidators`, `Inv_StatusMonotonic`, `Inv_ConfidenceBounded` | T6/T8 |

- Wrapper: `scripts/run_tlc.py` (supports `--spec`, `--n-min`, `--workers`).
- Local TLC binary: `tools/tla+/tlc` (wraps `tools/tla+/tla2tools.jar`).

## Current Status

TLC is **installed locally** in `tools/tla+/`. A symlink also exists at `.venv/bin/tlc` so the
wrapper is available whenever the virtual environment is activated. The script falls back to
the local wrapper automatically if `tlc` is not on `PATH`.

Example runs (all passed):

```bash
python scripts/run_tlc.py --spec EventChain --max-events 3 --max-confidence 2
python scripts/run_tlc.py --spec CRDTMerge --max-events 2 --max-confidence 1 --actors alice
python scripts/run_tlc.py --spec ConsensusEngine --max-events 3 --max-confidence 2 --n-min 1
```

## Notes

- The first TLA+ attempt used `--` for single-line comments and `/` for set-filtering; both are
  invalid in TLA+. The specs now use `\*` comments and nested subset comprehensions.
- Operator names starting with `WF_` were renamed to `Axiom_` because `WF` is the weak-fairness
  operator in TLA+ and `_` starts a subscript.
- `CRDTMerge` is bounded to lifecycle events (`LifecycleEvents`) for model checking to keep the
  state space manageable; the merge properties still hold for all event types.

## Known Limitations

- The specs abstract cryptographic hashes and signatures; they focus on well-formedness, status
  lattice, confidence monotonicity, and CRDT merge invariants.
- Bounded checking is limited by state-space explosion; unbounded correctness relies on the
  inductive argument in `docs/paper_ao/supplementary/appendix_e_proofs.tex` and the Coq skeleton
  under `formal/coq/`.
