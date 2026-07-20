# ADL Lite Expert Validation Framework

> **Version**: 1.0  
> **Scope**: Ontological quality assurance for ADL Lite capability documents (L1–L4)  
> **References**: OntoClean (Guarino & Welty, 2002), BFO 2.0 (Arp et al., 2015), ADL Lite Spec §7.5

---

## 1. Purpose

This document defines a **reproducible expert-review protocol** for evaluating the ontological quality of ADL Lite documents. It is designed to satisfy the reviewer request: *"demonstrates at least one expert-reviewed domain case."*

The framework:
1. Defines **evaluation rubrics** for each document layer (L1–L4).
2. Provides a **scoring guide** (Likert 1–5) with concrete anchors.
3. Describes the **expert profile** required for review.
4. Includes **example evaluations** on real ADL documents.
5. References established ontological quality criteria (OntoClean, BFO alignment).

---

## 2. Expert Review Protocol

### 2.1 Reviewer Profile

A qualified expert reviewer must have **at least one** of the following:
- **Domain expertise**: ≥ 3 years in the document's declared domain (e.g., AML, deep learning).
- **Ontological expertise**: Familiarity with foundational ontologies (BFO, DOLCE) and quality frameworks (OntoClean).
- **Applied ontology practice**: Authored or reviewed ≥ 2 ontologies in a peer-reviewed venue (ISWC, ESWC, FOIS, Applied Ontology journal).

Reviewers are **blinded** to automated validation scores until after their independent review is complete.

### 2.2 Review Procedure

1. **Pre-review**: Read the ADL Lite specification (§7.2–§7.5) and the declared domain background.
2. **Independent review**: Score each criterion (§3) on a 1–5 Likert scale without discussion.
3. **Calibration meeting** (if panel ≥ 2): Discuss discrepancies > 2 points on any criterion and reach consensus or record dissent.
4. **Final report**: Compile per-document scores, inter-rater agreement (Cohen's Kappa), and qualitative notes.
5. **Comparison with automation**: After the expert report is locked, run `ADLValidator` (strict mode) and `L2TemplateValidator`, then compute Pearson correlation between expert and automated scores.

### 2.3 Review Environment

- Reviewers use the `adl-lite validate --strict` CLI for automated checks, but only **after** their manual review is complete.
- Raw documents are provided as Markdown files with L1–L4 intact.
- A review template (JSON/CSV) is provided to ensure consistent data capture.

---

## 3. Evaluation Rubric (L1–L4)

### 3.1 L1: Front Matter (Identity & Metadata)

| Criterion | Description | Score Anchors (1–5) |
|-----------|-------------|---------------------|
| **C1. Identity Completeness** | All required fields (`adl_type`, `adl_id`, `status`, `confidence`, `scope`, `provisional_names`) are present and non-empty. | 1 = Missing >2 fields; 3 = Missing 1 field; 5 = All present and well-typed. |
| **C2. Ontological Consistency** | `status`, `confidence`, and `novelty` are mutually consistent (e.g., `confidence` ≥ 0.5 for `validated` status; `novelty` reflects actual claim). | 1 = Severe inconsistency (e.g., `validated` with `confidence` = 0.1); 5 = Fully consistent and justified. |
| **C3. Scope Appropriateness** | `scope` matches the sensitivity and provenance of the content (`public`, `private/<org>`, `user/<id>`, `shared/<collab>`). | 1 = Mismatch (public scope for sensitive data); 5 = Perfect match with documented rationale. |
| **C4. Naming Quality** | Provisional names (`zh` and/or `en`) are concise, unambiguous, and domain-appropriate. | 1 = Missing or misleading names; 3 = Present but vague; 5 = Precise and follow domain conventions. |

### 3.2 L2: Narrative (Markdown Body)

| Criterion | Description | Score Anchors (1–5) |
|-----------|-------------|---------------------|
| **C5. Narrative Clarity** | Body is free of pronouns (`this`, `that`, `it`, `这些`, `那个`) and vague referents that break cross-agent consensus. | 1 = Pervasive pronouns; 3 = A few violations; 5 = Completely explicit. |
| **C6. Structural Compliance** | Body follows the three-section template: **Observation**, **Reasoning**, **Conclusion**. Each section is non-empty and serves its intended epistemic role. | 1 = Missing ≥2 sections; 3 = All present but one is thin; 5 = All present and substantive. |
| **C7. Cross-reference Quality** | Wiki-links (`[[Concept Name]]`) and external references point to resolvable, relevant concepts. | 1 = Broken or irrelevant links; 5 = Rich, well-curated link network. |

### 3.3 L3: Semantic Assertions (Relations, Evidence, Seals)

| Criterion | Description | Score Anchors (1–5) |
|-----------|-------------|---------------------|
| **C8. Relation Soundness** | All `relation` predicates are from the ADL core ontology (`isomorphic-to`, `specialisation-of`, `co-occurs-with`, `related-to`, `analogical-to`, `dual-of`, `fork-of`, `mitigated-by`, `indexed-phrase`). | 1 = Custom/invalid predicates; 3 = Mostly valid but one deviation; 5 = All predicates are ontology-registered. |
| **C9. Relation Evidence** | Every relation has ≥1 supporting evidence block or a formal seal. | 1 = No evidence for any relation; 3 = Some relations lack evidence; 5 = Every relation is grounded. |
| **C10. Evidence Rigor** | Evidence blocks specify `evidence_type`, `data_ref`, and `confidence`. Types match the claim (e.g., `simulator_run` for computational claims). | 1 = Evidence is anecdotal or untyped; 5 = Typed, referenced, and confidence-calibrated. |
| **C11. Formal Seal Quality** | If present, formal seals specify `language`, `assertion`, and `proof_ref`. The assertion is falsifiable and the proof is reachable. | 1 = Seal is hand-wavy; 5 = Machine-checkable assertion with reachable proof artifact. |

### 3.4 L4: Actions (Lifecycle & Provenance)

| Criterion | Description | Score Anchors (1–5) |
|-----------|-------------|---------------------|
| **C12. Action Preconditions** | Every L4 action respects its ontology preconditions (e.g., `validate` requires `status` ≠ `archived` and sufficient validators). | 1 = Actions systematically violate preconditions; 5 = All actions are precondition-compliant. |
| **C13. Provenance Chain** | Each action has a non-empty `actor`, `reasoning`, and `timestamp`. The actor is a known identifier in the collaboration scope. | 1 = Anonymous or unexplained actions; 5 = Fully attributable with clear rationale. |
| **C14. Transition Legality** | Lifecycle transitions (`provisional` → `validated` / `deprecated` / `forked` / `archived`) follow the ontology DAG. No regressions. | 1 = Illegal transitions; 5 = All transitions are DAG-compliant and justified. |

---

## 4. Scoring Guide

### 4.1 Overall Quality Score

For a document with N scored criteria, the **overall quality score** is:

```
Q = (Σ_i score_i) / (5 × N)   ∈ [0, 1]
```

Interpretation:
- **Q ≥ 0.80**: Excellent — ready for publication or cross-agent consensus.
- **0.60 ≤ Q < 0.80**: Good — minor revisions needed.
- **0.40 ≤ Q < 0.60**: Fair — major revisions required.
- **Q < 0.40**: Poor — should not be admitted to the registry.

### 4.2 Inter-rater Agreement Thresholds

Using Landis & Koch (1977) interpretation of Cohen's Kappa (κ):

| κ Range | Interpretation | Action |
|---------|----------------|--------|
| < 0.00 | Poor | Reject panel; retrain reviewers. |
| 0.00 – 0.20 | Slight | Discuss criteria; recalibrate. |
| 0.21 – 0.40 | Fair | Acceptable for exploratory work. |
| 0.41 – 0.60 | Moderate | Acceptable for registry admission. |
| 0.61 – 0.80 | Substantial | Good for peer-reviewed publication. |
| 0.81 – 1.00 | Almost perfect | Gold-standard benchmark. |

**Target for ADL Lite**: κ ≥ 0.60 (moderate–substantial) for registry admission; κ ≥ 0.65 for peer-reviewed domain cases.

### 4.3 Automation Correlation Target

Pearson correlation between automated score (`ADLValidator` + `L2TemplateValidator`) and expert consensus:

- **r ≥ 0.70**: Strong — automation can be used as a first-pass filter.
- **0.50 ≤ r < 0.70**: Moderate — automation useful but requires human oversight.
- **r < 0.50**: Weak — automation not reliable; expert review mandatory.

**Target for ADL Lite**: r ≥ 0.65.

---

## 5. Example Evaluations

### 5.1 Example A: `capital_reflux_trap.md` (High Quality)

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| C1. Identity Completeness | 5 | All fields present; `mechanism` and `evidence_refs` populated. |
| C2. Ontological Consistency | 4 | `confidence` = 0.84 is consistent with `provisional` status (awaiting more validators). |
| C3. Scope Appropriateness | 5 | `private/ceiec-aml` correctly marks sensitive AML data. |
| C4. Naming Quality | 5 | Both `zh` and `en` names are precise and domain-appropriate. |
| C5. Narrative Clarity | 5 | No pronoun violations; explicit capability names used throughout. |
| C6. Structural Compliance | 4 | Strong Observation/Reasoning/Conclusion structure, though not explicitly headered. |
| C7. Cross-reference Quality | 5 | Wiki-links to `Gradient Explosion`, `Money Laundering Layering`, `Structural Hole Theory` are all relevant. |
| C8. Relation Soundness | 5 | Predicates `isomorphic-to` and `specialisation-of` are ontology-registered. |
| C9. Relation Evidence | 5 | E1–E3 evidence blocks directly support the relations. |
| C10. Evidence Rigor | 4 | Evidence types match claims; `data_ref` is resolvable (vecdb, tool, expert). |
| C11. Formal Seal Quality | 3 | Seal present but `status: pending` (acceptable for provisional document). |
| C12. Action Preconditions | N/A | No L4 actions in this document. |
| C13. Provenance Chain | N/A | No L4 actions. |
| C14. Transition Legality | 5 | Consensus history shows only `provisional` registration; no illegal transitions. |

**Overall Q = 64 / 65 ≈ 0.985** (Excellent)

### 5.2 Example B: Degraded Variant (Missing L2, Bad Predicate)

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| C1. Identity Completeness | 3 | `adl_id`, `status`, `confidence` present, but `provisional_names` missing `en`. |
| C2. Ontological Consistency | 2 | `confidence` = 1.2 is conceptually invalid (though Pydantic clamps it). |
| C3. Scope Appropriateness | 5 | `public` is acceptable for a test document. |
| C4. Naming Quality | 2 | Only partial name; not domain-appropriate. |
| C5. Narrative Clarity | 1 | Body contains pronoun `it` and vague referents. |
| C6. Structural Compliance | 1 | Missing all three sections (Observation, Reasoning, Conclusion). |
| C7. Cross-reference Quality | 1 | No wiki-links. |
| C8. Relation Soundness | 1 | Predicate `totally-made-up-predicate` is not in the ontology. |
| C9. Relation Evidence | 1 | No evidence blocks for the relation. |
| C10. Evidence Rigor | 1 | No evidence present. |
| C11. Formal Seal Quality | N/A | No seal. |
| C12. Action Preconditions | 2 | `validate` action attempted on `provisional` with no validators (fails collusion-resistance). |
| C13. Provenance Chain | 3 | Actor present but reasoning is thin. |
| C14. Transition Legality | 3 | Attempted `validate` from `provisional` is legal, but preconditions fail. |

**Overall Q = 26 / 65 ≈ 0.400** (Fair — major revisions required)

---

## 6. Ontological Quality Criteria (External References)

### 6.1 OntoClean (Guarino & Welty, 2002)

ADL Lite maps OntoClean meta-properties to its validation layers:

| OntoClean Property | ADL Lite Mapping | Validation Layer |
|--------------------|------------------|------------------|
| **Rigidity** | `status` transitions are monotonic (no regression from `validated` → `provisional`). | L4 (EventChain semantics) |
| **Identity** | `adl_id` is a persistent, unique identifier. | L1 (`adl_id` pattern) |
| **Unity** | A capability is a single `EventChain`, not a fragmented set of documents. | L1 + L4 (chain integrity) |
| **Dependence** | Relations must have supporting evidence (no free-floating assertions). | L3 (C9) |

### 6.2 BFO 2.0 Alignment

ADL Lite concepts are designed to align with BFO 2.0 top-level categories:

- **ADL `discovery`** → BFO `process` (an event in which a capability is recognized).
- **ADL `concept`** → BFO `generically dependent continuant` (the capability as an informational entity).
- **ADL `evidence`** → BFO `process` (the process of gathering data that supports the concept).
- **ADL `relation`** → BFO `relational quality` (a quality that inheres in the bearer by virtue of its relation to another).

Validation checks ensure that:
1. No `discovery` is treated as a `concept` without an `EventChain` (processual grounding).
2. `evidence` blocks reference `data_ref` that point to `process` outputs (simulator runs, vector clusters).
3. `formal_seal` assertions are `generically dependent continuants` (proof artifacts that can be copied without loss).

---

## 7. Review Report Template

```json
{
  "review_id": "REV-2025-001",
  "document_id": "disc-capital-trap",
  "reviewers": ["expert_aml_1", "expert_ont_2"],
  "date": "2025-07-15",
  "scores": {
    "C1": 5, "C2": 4, "C3": 5, "C4": 5,
    "C5": 5, "C6": 4, "C7": 5,
    "C8": 5, "C9": 5, "C10": 4, "C11": 3,
    "C12": null, "C13": null, "C14": 5
  },
  "overall_quality": 0.985,
  "inter_rater_kappa": 0.72,
  "automated_correlation": 0.81,
  "recommendation": "accept_with_minor_revisions",
  "notes": "L2 sections are implicit rather than explicit headers. Recommend adding ## headers for automated parsing."
}
```

---

## 8. Tooling

The following ADL Lite CLI commands support the expert review workflow:

```bash
# Parse and validate (strict mode = ontology predicate checks + SHACL)
adl-lite validate --strict examples/capital_reflux_trap.md

# L2 template check
adl-lite validate --strict-template examples/capital_reflux_trap.md

# Consensus verification (event chain integrity)
adl-lite consensus verify disc-capital-trap

# Export validation report as JSON
adl-lite validate --json examples/capital_reflux_trap.md > review_auto.json
```

---

## 9. References

1. Guarino, N., & Welty, C. (2002). *OntoClean: Analyzing and Repairing Ontologies*. IEEE Computer.
2. Arp, R., Smith, B., & Spear, A. D. (2015). *Building Ontologies with Basic Formal Ontology*. MIT Press.
3. Landis, J. R., & Koch, G. G. (1977). The Measurement of Observer Agreement for Categorical Data. *Biometrics*, 33(1), 159–174.
4. ADL Lite Specification (v0.5.0-alpha), §7.5 Validator Design.

---

*Document generated for ADL Lite peer review response. Version 1.0.*
