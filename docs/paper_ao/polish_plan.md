# ADL Lite Paper — Polish Pass Plan

## Objective
Apply `research-paper-refiner` skill to polish all sections of the ADL Lite paper for Applied Ontology journal submission.

## Target Journal
Applied Ontology (IOS Press) — formal ontology, philosophical foundations, operational semantics

## Polish Dimensions (per skill)
1. Grammar — subject-verb agreement, articles, dangling modifiers, run-on sentences
2. Word Choice — academic formality, precision, avoid colloquialisms
3. Voice & Tense — active/passive balance, tense consistency by section
4. Coherence & Cohesion — transitions, signal words, paragraph flow
5. Sentence Structure — variety, length balance, nominalization

## Section Assignments

| Worker | Sections | File(s) | Focus |
|--------|----------|---------|-------|
| Polisher_Abstract_Intro | Abstract + §1 Introduction | abstract.tex, 01_introduction.tex | Funnel structure, background→problem→contributions |
| Polisher_Related | §2 Related Work | 02_related_work.tex | Thematic grouping, objective critique, transitions |
| Polisher_Ontology | §3 Ontological Analysis | 03_ontological_analysis.tex | Philosophical precision, BFO/UFO terminology, formal definitions |
| Polisher_Arch | §4 Architecture | 04_architecture.tex | Theorem clarity, formal semantics, mathematical notation consistency |
| Polisher_Empirical | §5 Empirical Validation | 05_empirical_validation.tex | Results description, statistical language, figure/table references |
| Polisher_Discuss_Concl | §6 Discussion + §7 Conclusion | 06_discussion.tex, 07_conclusion.tex | Limitations framing, future work, contribution summary |
| Polisher_Appendices | Appendices A–F | appendix_*.tex | Consistency with main text, proof clarity, notation |

## Constraints
- Preserve all technical content, theorems, proofs, mathematical notation
- Preserve all citations and references
- Do not change the structure or argumentation flow
- Apply minimal changes — word/phrase level, not sentence/paragraph level unless necessary
- Flag any technical inconsistencies found during polishing

## Integration
After all workers complete, the orchestrator will:
1. Review flagged issues
2. Compile LaTeX to verify no errors
3. Produce final polished PDF
