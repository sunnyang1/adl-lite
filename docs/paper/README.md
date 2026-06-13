# ADL Lite Paper — AAMAS 2027 (Primary) / ESWC/ISWC 2027 (Backup)

This directory contains the complete paper submission materials for ADL Lite.

## Files

| File | Description |
|------|-------------|
| `PAPER_AAMAS_2027.pdf` | **Final revised paper** — PDF, AAMAS format (72 pp) |
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

## Paper Statistics

- **Word count**: ~35,000
- **Sections**: 7 + 6 Appendices
- **Experiments**: 16 (E1–E16) + E5 (planned) + E17 (planned)
- **Theorems**: 7 with proofs
- **Tables**: 15+
- **Algorithms**: 2

## Target Venues

1. **AAMAS 2027** (primary) — Autonomous Agents and Multi-Agent Systems
2. **ESWC 2027** or **ISWC 2027** (backup) — Semantic Web track

## Submission Checklist

- [x] Abstract (250 words)
- [x] Introduction with Agent Governance Landscape (KYA, AgentSafe, Talukdar, SafeAgent, Agent Traces)
- [x] Related Work (foundational ontologies, agent governance, event-centric modeling)
- [x] Ontological Analysis (BFO/DOLCE/UFO alignment, two-level account, identity axioms)
- [x] Architecture (L1-L4, EventChain, ActionExecutor, ConsensusEngine, formal semantics)
- [x] Formal semantics (7 theorems with proofs, Event Calculus/DL comparison)
- [x] Empirical Validation (E1–E6, E13–E16, honest framing, boundary conditions)
- [x] Discussion (agent governance landscape, limitations, complementary systems)
- [x] Appendices (PROV-O export, SHACL shapes, adversarial tests, reproducibility, proofs, RDF-star)
- [x] Response letter (3 rounds + agent governance rewrite)
