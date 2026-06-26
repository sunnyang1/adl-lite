# Applied Ontology Reviewer Response — Modification Plan

**Reviewer**: Applied Ontology (anonymous)
**Assessment**: Lean toward acceptance if formal and bibliographic gaps are addressed
**Date**: 2025-07-01
**Deadline**: 6 weeks (target: 2025-08-15)

## Reviewer Core Concerns (Prioritized)

### P0. Missing References (Must Fix)
- AgentHub (2510.03495) — agent registry framework
- Zhou G1-G3 (2603.14332) — governance requirements
- DIDs/VCs survey (2402.02455) — decentralized identity
- PROV-O survey (2407.17699) — provenance standardization
- Blockchain provenance survey (2606.10631)

### P1. Formalization Depth (Must Fix)
- Precondition language: complete formal syntax, semantics, complexity proof
- γ (confidence aggregation): exact definition with conflict handling rules
- Fork determinism: formal conditions and equivalence classes
- Theorems 1-7: sketch proofs in main text + full proofs in Appendix E

### P2. REVOKE Semantics (Must Fix)
- Discuss epistemic weakening vs. cessation design choice
- Clarify HoldsAt semantics (independent of confidence)
- Plan REVOKE event type in FW12

### P3. PROV-O Mapping (Must Fix)
- EventChain → PROV-O activity bundle mapping
- REGISTER/VALIDATE/DEPRECATE → prov:Activity subclasses
- Loss analysis: what ADL Lite semantics cannot map to PROV-O

### P4. Multi-Agent Case Study (Strongly Recommended)
- 3 agents, complete lifecycle: register → validate → dispute → fork → deprecate
- Near-duplicate reconciliation via L3 relations
- Downstream consumer usage of derived status/confidence

### P5. γ Ablation Study (Recommended)
- Microbenchmark: γ_default vs γ_agg vs γ_cal performance
- Precondition complexity (k rules) vs. evaluation time
- Storage overhead vs. Git-only / PROV-O-only baselines

### P6. LWW → CRDT Migration Path (Recommended)
- Which lifecycle events commute
- Which require conflict-resolution policies
- Blocklace integration plan

## Implementation Order

1. **Phase 1 (Week 1)**: References + PROV-O mapping + REVOKE semantics
2. **Phase 2 (Week 2)**: Precondition formalization + γ formalization
3. **Phase 3 (Week 3)**: Case study + ablation study
4. **Phase 4 (Week 4)**: Fork determinism + CRDT migration
5. **Phase 5 (Week 5-6)**: Polish, compile, review, push

## Files to Modify

- `docs/paper_ao/references.bib` — add 5+ new references
- `docs/paper_ao/sections/02_related_work.tex` — AgentHub, Zhou G1-G3, DIDs/VCs
- `docs/paper_ao/sections/04_architecture.tex` — precondition formalization, γ formalization, fork determinism
- `docs/paper_ao/sections/03_ontological_analysis.tex` — REVOKE semantics discussion
- `docs/paper_ao/sections/06_discussion.tex` — PROV-O mapping, case study, ablation
- `docs/paper_ao/sections/07_conclusion.tex` — updated future work
- `docs/paper_ao/sections/appendix_e.tex` — full proofs for Theorems 1-7
- `docs/paper_ao/sections/appendix_f.tex` — PROV-O mapping details
- `docs/paper_ao/supplementary/` — new files if needed

## Success Criteria

- [ ] All 5 missing references added and cited in §2/§6
- [ ] Precondition language has formal syntax, semantics, complexity proof in §4
- [ ] γ has exact mathematical definition with conflict handling in §4
- [ ] REVOKE semantics discussed in §3 with design rationale
- [ ] PROV-O mapping table in §6 with loss analysis
- [ ] Multi-agent case study in §5 or appendix
- [ ] γ ablation microbenchmark in §5
- [ ] Fork determinism formal conditions in §4
- [ ] All theorems have sketch proofs in main text + full proofs in Appendix E
- [ ] Paper compiles with zero errors
- [ ] All cross-references verified
