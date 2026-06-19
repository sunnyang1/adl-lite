# ADL Lite Paper — Applied Ontology (Primary) / ESWC/ISWC 2027 (Backup)

This directory contains the complete paper submission materials for ADL Lite.

## Files

| File | Description |
|------|-------------|
| `PAPER_APPLIED_ONTOLOGY.pdf` | **Final revised paper** — PDF, Applied Ontology format (35 pp) |
| `PAPER_ESWC_ISWC_2027.pdf` | **Backup submission** — PDF, Springer LNCS format |
| `REVIEW_RESPONSE.md` | Response to peer-review comments |
| `EVENT_FIRST_DRAFT.md` | Original draft (baseline) |

## Paper Title

**ADL Lite: An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems**

## Key Positioning

ADL Lite is a **complementary governance layer**, not a competing ontology production method. It fills the gap between:
- **KYA** (permissions layer, HMAC chain)
- **AgentSafe** (architecture-level governance, design-time + runtime + audit)
- **LLM-native OE** (Talukdar et al., LLM4ACOE — produces ontologies without lifecycle governance)

## Review Response History

- `RESPONSE_ROUND1.md` — First round (PROV-O mapping, threat model, Git baseline E7)
- `RESPONSE_ROUND2.md` — Second round (CIDOC CRM, CRDTs, SHACL/ShEx comparison)
- `RESPONSE_ROUND3.md` — Third round (formal theorems, hash spec, PROV-O/SHACL appendices, agent governance landscape)
- `RESPONSE_ROUND4.md` — Fourth round (paper restructuring, phase labels removed, near-duplicate detection, multi-agent examples, canon_version)

## Paper Statistics

- **Word count**: ~18,000
- **Sections**: 7 + 6 Appendices
- **Experiments**: 18 (E1–E6, E9, E13–E16, E17–E20b, E21, E23)
- **Theorems**: 9 (T1–T9) with proofs
- **Tables**: 15+
- **Algorithms**: 2

## Target Venues

1. **Applied Ontology** (primary) — IOS Press journal
2. **ESWC 2027** or **ISWC 2027** (backup) — Semantic Web track

## Submission Checklist

- [x] Abstract (250 words)
- [x] Introduction with Agent Governance Landscape (KYA, AgentSafe, Talukdar, SafeAgent, Agent Traces)
- [x] Related Work (foundational ontologies, agent governance, event-centric modeling)
- [x] Ontological Analysis (BFO/DOLCE/UFO alignment, two-level account, identity axioms, OntoClean)
- [x] Architecture (L1-L4, EventChain, ActionExecutor, ConsensusEngine, formal semantics, 12 axioms)
- [x] Formal semantics (9 theorems with proofs, TLA+ spec, Event Calculus/DL comparison)
- [x] Empirical Validation (E1–E6, E13–E16, E20–E23, honest framing, boundary conditions)
- [x] Discussion (agent governance landscape, limitations, complementary systems, future work)
- [x] Appendices (PROV-O export, SHACL shapes, adversarial tests, reproducibility, proofs, RDF-star)
- [x] Response letter (4 rounds + agent governance rewrite)
- [x] Code-paper alignment (590 tests, 12-axiom well-formedness, CRDT merge, calibration formulas)
