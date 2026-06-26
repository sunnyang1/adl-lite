# ADL Lite Coq/Iris Formalisation Skeleton

This directory contains a minimal Coq formalisation skeleton for the core
ADL Lite event-chain semantics.  It is intended as a starting point for
machine-checked proofs of the invariants described in the project paper.

## Structure

```
formal/coq/
├── _CoqProject            # CoqProject file (-R theories ADL, -R iris ADL.Iris)
├── Makefile               # Delegates to coq_makefile-generated Makefile.coq
├── dune-project           # Optional Dune 3.8 project
├── adl_lite.opam          # opam package metadata
├── README.md              # This file
├── theories/              # Core Coq theories (no Iris dependency)
│   ├── Status.v           # Status lattice, leq, LUB, monotonicity (T3)
│   ├── Event.v            # Event type and StatusOf mapping
│   ├── Confidence.v       # Confidence max / boundedness (T4)
│   ├── Chain.v            # Chain well-formedness axioms and preservation (T7)
│   ├── Invariants.v       # Top-level theorem statements/proofs
│   └── CRDT.v             # Branch merge and CRDT properties (T9)
└── iris/                  # Optional Iris separation-logic stubs
    ├── event_chain_ra.v   # Resource algebra placeholder
    └── concurrent_append.v # Hoare triple stub for split-lock append
```

## Building with `make`

Requires Coq 8.18+ and, optionally, `coq-mathcomp-ssreflect` and Iris.

```bash
cd formal/coq
make
```

The `Makefile` regenerates `Makefile.coq` from `_CoqProject` whenever the
latter changes and then delegates to it.  Other targets:

```bash
make clean   # remove generated files
make html    # generate Coqdoc HTML
```

If you prefer Dune:

```bash
dune build
```

## Theorems intended

| Theorem | File | Statement |
|---------|------|-----------|
| T3 | `Status.v`, `Invariants.v` | Status derivation is monotone w.r.t. chain prefixes. |
| T4 | `Confidence.v`, `Invariants.v` | Event and derived confidence are bounded by `MaxConfidence`. |
| T7 | `Chain.v`, `Invariants.v` | Appending a valid event preserves chain well-formedness. |
| T9 | `CRDT.v` | Branch merge is commutative, associative, idempotent, and preserves well-formedness. |

## Iris files

Files under `iris/` are optional stubs.  They do not import the Iris library
by default; instead they provide placeholder definitions so the core theories
still compile when Iris is not installed.  Once Iris is available, replace the
fallback module in `iris/event_chain_ra.v` with the real Iris resource-algebra
construction and complete the `append_spec` proof in `iris/concurrent_append.v`.
