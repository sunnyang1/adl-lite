# ADL Lite — External Reviewer Brief: Applied Ontology

> **Role:** Applied Ontology / Upper Ontology Reviewer  
> **Focus:** Ontological analysis (§3), upper-ontology mappings (Table 2), OntoClean evaluation, OWL 2 DL fragment (Appendix A), BFO/DOLCE/UFO alignment, deviations, and costs  
> **Paper length:** 49 pages (main) + 21 pages (supplementary)  
> **Target venue:** Applied Ontology (ESWC/ISWC 2027 track)

---

## Paper Summary (for Reviewer Context)

ADL Lite is an **event-first** operational ontology for multi-agent LLM capability governance. It inverts the traditional object-first ontology engineering stance (e.g., Palantir Foundry, OWL) by treating events (occurrents/perdurants) as the fundamental ontological primitive and concepts as generically dependent continuants derived from event histories. The paper maps ADL Lite categories to BFO 2.0, DOLCE, and UFO, and provides a partial OWL 2 DL axiomatization for interoperability with BFO-based tools (e.g., ROBOT).

---

## Sections to Focus On

| Section | Lines | What to Check |
|---------|-------|---------------|
| §3.1 Philosophical Foundation | ~15 lines | Wittgenstein §1.1 citation, event-first stance justification |
| §3.2 Categories and Taxonomy | ~120 lines | Table 2 (upper-ontology mapping), four category subsections |
| §3.3 Identity Conditions | ~80 lines | Event identity, Concept identity, EventChain identity, OntoClean meta-properties |
| §3.4 Ontological Dependence | ~80 lines | GDC→ICE→Markdown dependence chain, Fine's rigid existential dependence |
| §3.5 Formal Alignment Fragment | ~5 lines | OWL 2 DL axiomatization claim, ROBOT compatibility |
| §3.6 Comparison with Upper Ontologies | ~30 lines | Three deviations, interoperability costs |
| Appendix A (PROV-O Export) | ~35 lines | Concrete PROV-O/IAO mappings, round-trip fidelity |
| Appendix F (RDF-star) | ~75 lines | RDF-star interoperability, reversible mapping |
| Appendix B (SHACL) | varies | SHACL shape for L3 relation validation |

---

## Concrete Review Questions (Checklist)

### Upper Ontology Mapping (Table 2)

- [ ] **Event as occurrent/perdurant:** Is the mapping to BFO `occurrent` and DOLCE `perdurant` correct? The paper says events have "no spatial extent" — is this consistent with BFO's definition of occurrents (which can have spatial location)?
- [ ] **EventChain as process:** The paper maps EventChain to BFO `process` and DOLCE `accomplishment` (approximate). Is an EventChain (a *sequence* of events) truly a process, or is it a *plan* (a type of process)? In BFO, a process is *unfolding in time*; an EventChain-record is static. The paper resolves this via the two-level account — is this resolution convincing?
- [ ] **Concept as GDC:** The paper maps Concept to BFO `generically_dependent_continuant` and DOLCE `non-physical_object` (approximate). Is a "concept" (a capability definition, e.g., "money-laundering pattern") truly a GDC? The paper argues it depends on the EventChain *record* (ICE) rather than the EventChain *process* — is this consistent with BFO's GDC criteria?
- [ ] **Relation as relational quality / relator:** The paper maps L3 relations to BFO `relational_quality` and UFO `relator`. Is an `isomorphic-to` relation between two concepts a relational quality? BFO relational qualities *inhere* in one continuant; the paper says the relation "inheres in the source concept" — is this the correct reading of BFO?
- [ ] **Actor as agent:** The paper maps Actor to BFO `agent` and DOLCE `physical_agent`. Can a software agent (LLM) be a DOLCE `physical_agent`? DOLCE physical agents are typically human or embodied; the paper may need to flag this as approximate.
- [ ] **Hash as GDC:** The paper maps `hash` to BFO `generically_dependent_continuant` with no DOLCE equivalent. Is a SHA-256 hash string a GDC? It is an information content entity (ICE), which is a GDC, but the mapping is thin.

### Two-Level Ontological Account (§3.2.4)

- [ ] **Axiom I1 (Event identity):** Events are individuated by UUID. Is this ontologically sufficient? Two events with identical content but different UUIDs are *different events*. Is this consistent with the intuition that a "validation event" is defined by its content (actor, concept, timestamp), not just its UUID?
- [ ] **Axiom I2 (Concept identity):** Concepts are content-addressed by genesis hash. The paper says "Two concepts with the same concept_id but different genesis hashes are different concepts." Is this a realistic scenario? If so, is the human-readable alias (`concept_id`) doing useful work, or is it a source of confusion?
- [ ] **Axiom I3/I4 (Chain record vs. process identity):** The paper distinguishes EventChain-record (ICE, continuant) from EventChain-process (occurrent). Is this distinction *necessary* for the ontology, or is it a philosophical finesse? Does it affect the engineering design?
- [ ] **Axiom D5 (No cross-level identity):** The paper asserts "No occurrent is identical to any ICE." This is a BFO constraint. Is ADL Lite *committed* to BFO, or is it merely *aligned* with BFO? If the former, the constraint is binding; if the latter, it is a design choice that could be relaxed.

### OntoClean Evaluation (§3.3.2)

- [ ] **Rigidity of Concept:** The paper claims Concept satisfies the **rigidity** criterion: "a concept's identity (genesis hash) is essential to it." Is this correct? In OntoClean, a rigid property is one that *must* hold for all instances of the class. Does the genesis hash *always* hold for a Concept? The paper says yes. Is this consistent with the fork semantics, where a forked concept has a *different* genesis hash?
- [ ] **Unity of Concept:** The paper claims Concept satisfies the **unity** criterion. Is a concept a "maximally self-connected entity"? The paper contrasts it with EventChain (a "mereological sum of events with no unified whole"). Is this distinction defensible?
- [ ] **Dependence of Concept:** The paper claims Concept is a **rigid existentially dependent** entity on the EventChain record. Is this stronger than generic dependence? Fine's rigid existential dependence (1995) requires that the dependent entity *cannot* exist without that *specific* bearer. The paper says the concept depends on the EventChain record (not any specific copy), which sounds like *generic* dependence, not *rigid* dependence. Is this a terminological slip?
- [ ] **Identity under fork:** The paper says "A forked concept is a different concept because it has a different genesis event." This is consistent with rigidity. But does the fork relationship (`fork-of` predicate) introduce a non-rigid property? The paper says the fork relationship is a UFO:Relator, not a property of the Concept.

### OWL 2 DL Fragment (§3.5, Appendix A)

- [ ] **Coverage:** The fragment declares `adl:Event` ⊂ `bfo:occurrent`, `adl:EventChain` ⊂ `bfo:process`, `adl:Concept` ⊂ `bfo:generically_dependent_continuant`, and two datatype properties (`hasPreviousHash`, `hasSHA256Hash`). Is this fragment *sufficient* for any useful reasoning? The paper admits it does not capture $\delta(C)$ or $\gamma(C)$, which go beyond OWL 2 DL. Is the fragment then merely a "starting point"?
- [ ] **ROBOT compatibility:** The paper claims the fragment enables "ROBOT consistency checking." Has this actually been tested? The fragment is provided as supplementary material but may not be syntactically valid OWL 2 DL without namespace declarations and imports.
- [ ] **PROV-O round-trip:** The paper claims PROV-O export is "lossless" round-trip. Is this verified? Appendix A says "Re-importing the Turtle file into ADL Lite reconstructs the original EventChain with identical event_ids and hashes." Has this been implemented and tested?
- [ ] **RDF-star mapping:** Appendix F claims the mapping to RDF-star is reversible with an extension. Is this extension actually implemented in the codebase? The paper says it is "possible" — has it been done?

### Deviations and Costs (§3.6)

- [ ] **Deviation 1 (No continuant/occurrent distinction at language level):** The paper admits this prevents direct BFO module import. Is this cost *acceptable* for an Applied Ontology venue? The paper argues it is necessary for Markdown-native authoring. Is the trade-off justified?
- [ ] **Deviation 2 (No explicit quality hierarchy):** The paper says qualities are encoded as payload fields. This means ADL Lite cannot reuse DOLCE's quality taxonomy. Is this a significant limitation for the target domain (capability governance), or is it a reasonable simplification?
- [ ] **Deviation 3 (Actions as first-class citizens):** The paper says actions are "co-equal" with objects. This prevents direct reuse of UFO-B's process hierarchy. The paper claims UFO-B's "Institutional Event" category is still compatible. Is this alignment actually established, or is it merely suggested?
- [ ] **Horn-clause claim:** The paper says preconditions are a "Horn-clause fragment of FOL." This is a formal semantics claim, but it is discussed in the ontology section (§3.6). Is this a category error? Horn-clause logic is a formal logic concept, not an ontological one.

---

## Known Issues to Flag (Pre-emptive Honesty)

1. **OWL 2 DL fragment is minimal:** The fragment is intentionally partial. It does not cover derivation functions, preconditions, or the action registry. Full bidirectional automation is scoped to future work (FW1).
2. **PROV-O round-trip claim:** The claim of lossless round-trip is stated but the full implementation details are not in the main text. The Turtle serialization is "omitted for brevity" in Appendix A.
3. **RDF-star reversible mapping:** The reversible mapping is described as "possible" but may not be fully implemented in the v0.2 codebase.
4. **Terminological slip (dependence):** The paper uses both "generic dependence" (BFO) and "rigid existential dependence" (Fine) somewhat interchangeably. These are distinct concepts in the literature. The reviewer may flag this.
5. **DOLCE `physical_agent` for LLMs:** The mapping of software agents to DOLCE `physical_agent` is approximate. A more precise mapping would be to DOLCE `agent` (if it exists) or a custom category.

---

## Deliverable

Please return a **review report** with:
- **Major issues:** Any ontological mapping that is fundamentally wrong, any category error, or any deviation that undermines the paper's credibility.
- **Minor issues:** Mapping approximations, terminological inconsistencies, or missing formalizations that are easily fixable.
- **Questions:** Anything that needs clarification from the authors.
- **Verdict:** Accept / Minor revision / Major revision / Reject (with rationale focused on ontological soundness and alignment quality).

---

*Generated: 2025-06-16 | Paper version: v0.3.5 (Month 2, Week 7)*
