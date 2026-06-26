# ADL Lite Paper Rewrite Plan

## New Title

**ADL Lite: An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems**

## Narrative Arc (New Story)

**Old arc:** "We built a new kind of operational ontology for concept lifecycle governance."
**New arc:** "LLM agents are proliferating across ecosystems. Each agent advertises capabilities (tools, APIs, knowledge domains). But who records what a tool can do, how it evolves, and whether it's trustworthy? Existing governance layers (KYA, AgentSafe) cover permissions and architecture, but not the lightweight, verifiable, lifecycle-aware registry of agent capabilities. ADL Lite fills that gap: an event-first, append-only, cryptographically linked Capability-Lifecycle Registry that treats every capability claim, validation, deprecation, and fork as an auditable event."

## What Stays (Strong Technical Content)

| Section | What Stays |
|---------|-----------|
| Architecture (Section 4) | Formal semantics, all 7 theorems, event algebra, fork/confluence, derivation functions, precondition language, decidability proof, comparison with EC/SC/DL, trust model, threat model table, recovery strategies, TLA+ specification note |
| Ontological Analysis (Section 3) | BFO/DOLCE/UFO alignment, two-level account, identity axioms, dependence axioms, identity conditions, relation lifecycle, all equations, axioms I1-I4, D1-D5, UFO instantiation, relator theory, identity persistence across re-materialization, cessation of existence |
| Empirical (Section 5) | E1-E4, E13-E16 results, E12 comparative benchmark, scale-up projections (but honest about E6 synthetic events) |
| Appendix references | All appendix references |
| L1-L4 document model | Full description |

## What Changes (Framing, Positioning, and References)

### 1. main.tex
- Title: `ADL Lite: An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems`
- Keywords: Add `agent governance`, `capability registry`, `lifecycle governance`; keep `event sourcing`, `multi-agent systems`, `provenance`
- Remove `ontology engineering`, `BFO`, `DOLCE`, `UFO` from keywords (keep them in body)

### 2. Abstract
**New framing:**
- Open with the LLM agent ecosystem problem: agents proliferating, capabilities advertised but not governed
- ADL Lite as the "missing layer" between permissions (KYA) and architecture governance (AgentSafe)
- EventChain as the mechanism: every capability claim, validation, deprecation, fork is a cryptographically linked event
- Keep the 7 theorems, but frame them as properties of a capability registry
- Keep E1-E6 results, but reframe E6 as capability-import stress test
- Position as a "framework paper" for capability governance

### 3. Introduction (Section 1)
**Subsection 1.1: Background**
- Replace "object-first to event-first OE" narrative with "LLM agent capability gap" narrative
- Introduce: (a) KYA - framework-agnostic trust layer with permissions but no lifecycle governance; (b) AgentSafe - architecture-level governance but heavyweight; (c) LLM-native OE - produces ontologies but no runtime governance
- Define the gap: **no lightweight, event-sourced, verifiable capability registry** exists that bridges these
- Keep the "operational ontology" definition but frame it as capability governance, not concept governance
- Wittgenstein Tractatus §1.1 stays as philosophical anchor

**Subsection 1.2: Research Gap**
- Restate: "How can we achieve lifecycle-aware, multi-agent capability governance without requiring object-first mutable state, heavy infrastructure, or proprietary interfaces?"
- Keep engineering + ontological dimensions, but reframe as capability governance

**Subsection 1.3: Contributions**
- Reframe all three contributions as capability-registry properties
- Keep the same technical content

**Subsection 1.4: Phase Definitions**
- Keep as-is, but reframe as capability registry phases

**Subsection 1.5: Paper Organization**
- Add "Section 2 positions ADL Lite within the emerging agent governance landscape (KYA, AgentSafe, Agent Traces to Trust, etc.)"

### 4. Related Work (Section 2) - MAJOR REWRITE
**New subsection structure:**

- **2.1: Agent Governance Landscape** (NEW)
  - KYA (arXiv:2605.25376): Framework-agnostic trust layer, HMAC chain, ~1,800 ops/sec, covers permissions but no capability lifecycle
  - AgentSafe (arXiv:2512.03180): Unified governance (design-time + runtime + audit), architecture-level, heavyweight
  - "From Agent Traces to Trust" (arXiv:2606.04990): Unified provenance, explicitly says "unified trace schema is still needed" - ADL Lite IS that schema
  - Talukdar et al. (arXiv:2604.23090): Multi-agent LLM ontology engineering, but produces static OWL without lifecycle governance
  - SafeAgent (arXiv:2604.17562): Safety protocol for LLM agents, protocol-level governance
  - Positioning: ADL Lite fills the gap between these - not a competitor but a complementary registry layer
  - **Key claim:** ADL Lite is NOT a "fourth route" in LLM-native OE. It is a complementary governance layer that adds lifecycle governance to whatever ontologies agents produce.

- **2.2: Foundational Ontologies and Event-First Semantics** (renamed from 2.1)
  - Keep BFO/DOLCE/UFO content
  - Rephrase: "ADL Lite's capability events correspond to BFO's occurrent..."

- **2.3: Knowledge Graph and Ontology Engineering** (renamed from 2.2)
  - Keep OWL/SPARQL, Palantir, lightweight alternatives content
  - Add: "LLM agents produce conceptual artifacts at high velocity; traditional OE workflows cannot govern their lifecycle."
  - Keep LLM-native OE subsection but frame as "existing approaches produce ontologies, not govern them"
  - Remove the "ADL Lite represents a fourth route" claim. Replace with "ADL Lite is a governance layer that can wrap any ontology produced by any route."

- **2.4: Provenance, Trust, and Verifiable Publishing** (renamed from 2.3)
  - Keep PROV-O, nanopublications, Trusty URIs, Git-native systems, institutional semantics

- **2.5: Event-Centric Ontologies** (renamed from 2.4)
  - Keep CIDOC CRM, SEM/LODE, SEO, Blocklace, occurrence-only, UFO-B, CRDTs
  - Frame as "event-first provenance mechanisms that support but do not govern capability lifecycles"

- **2.6: Positioning** (renamed from 2.5)
  - Update table to include KYA, AgentSafe as reference approaches
  - Show ADL Lite fills the gap: lightweight + lifecycle-aware + verifiable

### 5. Architecture (Section 4) - MINOR REWRITE
- Keep all formal semantics, all 7 theorems, all equations, all proofs
- **Theorem 5 fix:** Add "non-colluding" premise (collusion caveat)
- Reframe all language: "concept" → "capability" where appropriate (but keep "concept" as the internal term, since EventChain is generic)
- Keep the document model (L1-L4) but frame as capability documentation layers
- **Key change:** The internal architecture doesn't change; only the framing does

### 6. Empirical Validation (Section 5) - MODERATE REWRITE
- **Honest E6 framing:** "9,000 REGISTER events (96.8%) from IBM AML transaction import, 200 VALIDATE (2.2%) and 50 DEPRECATE (0.5%) synthetic governance events. This stress-test validates the EventChain architecture at scale, not domain-level AML effectiveness."
- **Theorem 5 collusion caveat:** In the architecture section, add explicit "non-colluding" premise to Theorem 5
- **E5 update:** "Pilot design for LLM-agent capability evaluation is underway. Preliminary results show..." (if we have any preliminary data from Sello or other sources)
- **E17 mention:** If we have any E17 results, add them. If not, state as planned
- Keep all E1-E4, E13-E16 results
- Remove E5 claim about AML expert evaluation if not yet done (or reframe as planned)

### 7. Discussion (Section 6) - MODERATE REWRITE
- **6.1:** Reframe "Event-First Architecture: Ontological Implications" → "Capability-First Governance: Ontological Implications"
- **6.2:** Update reviewer Q&A with new references
- **6.3:** Conceptual Modeling Contribution → Capability Registry Contribution
- **6.4:** Limitations - keep all 10, but reframe L1-L10 in capability governance language
- **6.5:** Comparison with Foundational Ontologies - keep
- **6.6:** Complementary Systems - add KYA, AgentSafe as complementary systems
- **NEW 6.7: The Agent Governance Landscape** - discuss how ADL Lite complements KYA, AgentSafe, etc.

### 8. Conclusion (Section 7) - MINOR REWRITE
- Restate contributions in capability-registry language
- Keep all future work (FW1-FW12)

### 9. references.bib - MAJOR FIX
- Remove all `REPLACES:` placeholder comments (6 entries: ref6, ref7, ref8, ref14, ref16, ref59)
- Merge the replacement entries into the main bibliography (glimm2014hermit, sirin2007pellet, hogan2021knowledge, guha2016schemaorg, dendron2020, foam2020, hemid2024ontoeditor)
- Add new verified references:
  - KYA: `arXiv:2605.25376` - Framework-Agnostic Agent Trust with HMAC Chain
  - AgentSafe: `arXiv:2512.03180` - Unified Agent Governance Framework
  - SafeAgent: `arXiv:2604.17562` - Safety Protocol for LLM Agents
  - "From Agent Traces to Trust": `arXiv:2606.04990` - Unified Provenance Framework
  - Talukdar et al.: `arXiv:2604.23090` - Multi-Agent LLM Ontology Engineering
  - Sello: `arXiv:2606.04193` - LLM Agent benchmark (if relevant for E5/E17)
- Fix ref59 issue: Remove the "CRDTs for KG editing" claim. The Hemid paper uses OT, not CRDTs. Replace with a factual statement.
- Ensure no duplicate entries remain

## Verification Steps

1. Check all internal cross-references still valid (\label, \ref, \cite)
2. Check LaTeX compiles successfully
3. Check that the word "ontology" is still used appropriately (it's not eliminated, but recontextualized)
4. Check that "capability" is used consistently as the new framing term
5. Verify the bibliography has no duplicate entries
6. Verify all new references are properly cited

## Output File Mapping

| File | Action |
|------|--------|
| main.tex | Edit title, keywords |
| sections/abstract.tex | Full rewrite |
| sections/01_introduction.tex | Full rewrite |
| sections/02_related_work.tex | Full rewrite |
| sections/03_ontological_analysis.tex | Minor edits (terminology) |
| sections/04_architecture.tex | Minor edits (Theorem 5 fix, terminology) |
| sections/05_empirical_validation.tex | Moderate rewrite (E6 honesty, E5 update) |
| sections/06_discussion.tex | Moderate rewrite (new subsection 6.7) |
| sections/07_conclusion.tex | Minor rewrite |
| references.bib | Major fix (merge placeholders, add new refs) |
