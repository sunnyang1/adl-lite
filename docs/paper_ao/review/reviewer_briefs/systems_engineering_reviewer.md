# ADL Lite — External Reviewer Brief: Systems Engineering

> **Role:** Systems Engineering / Empirical Validation Reviewer  
> **Focus:** Experimental design (§5), reproducibility (Appendix D), adversarial trials (Appendix C), comparative evaluation (E12, E19), performance claims, threat model honesty  
> **Paper length:** 49 pages (main) + 21 pages (supplementary)  
> **Target venue:** Applied Ontology (ESWC/ISWC 2027 track)

---

## Paper Summary (for Reviewer Context)

ADL Lite is a Python package implementing an event-first capability registry. The paper validates the architecture through **11 core experiments** (E1–E11) plus **8 extended experiments** (E12–E19), covering chain integrity, status derivation, snapshot consistency, precondition enforcement, scalability, adversarial robustness, multi-agent simulation, and comparative governance cost analysis. All experiments are executable via `python -m experiments.runner all` with a Docker reproduction environment.

---

## Sections to Focus On

| Section | Lines | What to Check |
|---------|-------|---------------|
| §5.1 Validation Strategy | ~5 lines | Correctness framing (verification, not generalization) |
| §5.2–5.5 Core Experiments (E1–E4, E6) | ~35 lines | Integrity, derivation, snapshot, precondition, scalability |
| §5.6 Boundary Conditions (E13–E16) | ~10 lines | Negative results, collusion vulnerability, defense-in-depth gaps |
| §5.7 Adversarial Trials (E4e-ext) | ~25 lines | 7 detectable + 4 undetectable attack scenarios |
| §5.8 Multi-Agent Simulation (E17) | ~5 lines | Precondition effectiveness (89.7%) — simulated, not real |
| §5.9 Head-to-Head (E19) | ~20 lines | Comparative governance cost — **author-estimated**, not measured |
| §5.10 Artifact Availability | ~5 lines | Docker, pip install, reproducibility scripts |
| §5.11 Comparative Evaluation (E12) | ~30 lines | Tables 6 and 7: qualitative + quantitative comparisons |
| Appendix C (Adversarial) | ~80 lines | 12 attack classes, 57 test cases, detection rates |
| Appendix D (Reproducibility) | ~60 lines | Runner infrastructure, Docker, expected runtimes |
| Appendix L (E19 Details) | varies | Full task definitions, pseudocode, sensitivity analysis |
| Appendix F (Comparative) | varies | Full interpretation of governance efficacy, failure modes |

---

## Concrete Review Questions (Checklist)

### Experimental Design

- [ ] **Verification vs. generalization:** The paper explicitly frames experiments as "verification tests, not generalisation experiments." Is this framing honest? Does the venue expect generalization experiments, or is verification sufficient for a systems paper?
- [ ] **Exhaustive vs. sampled:** E2 tests "all event sequences of length up to 3" (2,204 cases). Is this exhaustive enumeration or sampling? For a 5-event alphabet, length-3 sequences = $5^3 = 125$; with 7 edge cases = 132. The paper says 2,204 cases — how is this number derived? (Likely: all sequences over the full alphabet including communication events, or combinations with multiple events.)
- [ ] **Hardware specification:** All timings are on Apple M2 (8P+4E cores, 3.49 GHz), 16 GB LPDDR5, macOS 14, Python 3.10. Is this hardware representative? Should the paper include a Linux/x86 baseline?
- [ ] **Pydantic overhead:** E6 attributes 58.4% of latency to Pydantic materialization. Is this measured or estimated? Can it be reproduced by disabling Pydantic validation?
- [ ] **Synthetic event generation:** The AML dataset (E6) uses "synthetically injected governance events." Is the synthetic generation strategy documented? Does it affect the validity of the scalability claim?

### Reproducibility

- [ ] **Docker environment:** The paper provides a Dockerfile. Is it actually tested? Does it build without errors on a clean machine?
- [ ] **Dependency pinning:** `requirements.txt` is mentioned. Are versions pinned? Does the paper specify exact versions for all critical dependencies (Pydantic, PyYAML, networkx)?
- [ ] **One-command reproduction:** The paper claims `docker run --rm adl-lite-repro python -m experiments.runner all` reproduces all experiments. Is this verified? What is the expected runtime (~5 minutes)?
- [ ] **Hardware specs file:** `docs/experiments/HARDWARE_SPECS.md` is referenced. Is this file actually present in the repository?
- [ ] **LaTeX environment:** The Dockerfile includes "pre-built LaTeX environment (TeX Live 2024)." Is this necessary? It adds significant image size.
- [ ] **Dataset availability:** The IBM AML HI-Small dataset is used. Is it publicly available? The paper says "pre-downloaded and cached" in the Docker image — does this comply with the dataset license?

### Performance Claims

- [ ] **Throughput claim:** E6 reports 20,847 events/sec. Is this throughput sustained or peak? What is the variance ($\sigma = 312$)? Is the CV (1.5%) acceptable?
- [ ] **Scale-up projection:** E6b projects linear scaling to 1M events ($\approx$47.7 s). Is this extrapolation justified? The paper says "linear extrapolations, not empirical validations" — is this honesty sufficient, or should the projection be removed?
- [ ] **E12 throughput claim:** 135k events/sec for verification. Is this the same operation as E6's 20,847 events/sec? If not, what is the difference? (Likely: E12 is hash-only verification; E6 includes full EventChain construction with Pydantic.)
- [ ] **Comparative benchmark:** Table 7 compares ADL Lite (measured) against nanopubs (published) and PROV-O (published). The footnote says "Estimated from published specifications; not empirically measured on identical hardware." Is this comparison fair? Should the paper run the baselines on the same hardware?
- [ ] **Latency claims:** E19 reports estimated latency (5.2 ms for ADL Lite vs. 25.5 ms for nanopubs). These are **author estimates**, not measured. The table caption says "All values are author estimates." Is this honest, or should the paper either measure them or remove the table?

### Adversarial Robustness

- [ ] **Detection vs. prevention:** Appendix C states "The current suite tests detection but not prevention." Is this acceptable? The paper says ADL Lite v0.2 does not implement Byzantine fault tolerance or actor authentication. Is the honest reporting of limitations sufficient?
- [ ] **A9 impersonation:** Attack A9 (impersonation) is **not detected** in Phase 1. The paper says "social audit only." Is this a critical vulnerability? Does the paper adequately explain that Phase 1.5/3 addresses this?
- [ ] **A11 selective omission:** Attack A11 is detected as $\circ$ (hash break in Phase 1, anchor mismatch in Phase 1.5). Is this sufficient, or does it require active prevention?
- [ ] **Phase 3 ablation:** A12 tests Phase 3 mechanisms disabled. Does this confirm additive security, or is it a straw-man test?
- [ ] **SHA-256 collision resistance:** A5 tests collision resistance via birthday-attack simulation. Is this test meaningful for a 256-bit hash? The expected operations for a birthday attack are $2^{128}$ — far beyond any test budget. The test verifies that no collision is found within the budget, but this is trivially true.

### Comparative Evaluation (E12, E19)

- [ ] **E19 author estimates:** The entire E19 table is labeled "author estimates." Is this a valid contribution? The paper says it is a "preliminary design" for a head-to-head comparison. Should this be framed as a "conceptual comparison" rather than an "empirical benchmark"?
- [ ] **Nanopub baseline:** The nanopub baseline uses "31–86% non-assertion triples" overhead. Is this citation accurate? Does it reflect the current state of nanopublication technology?
- [ ] **PROV-O baseline:** The PROV-O baseline is described as requiring "RDF triplestore + PROV tooling." Is this a fair comparison? PROV-O is a data model, not a system; the comparison is between ADL Lite and a *PROV-O-based pipeline*, not PROV-O itself.
- [ ] **Git-only baseline:** The Git-only baseline is described as having 0/4 completed governance tasks. Is this a straw-man? Git is a version control system, not a governance system; comparing it to ADL Lite on governance tasks is inherently unfair.
- [ ] **Qualitative comparison (Table 6):** The qualitative comparison uses $\checkmark$/$\circ$/$\times$ ratings. Are these ratings justified? Do they reflect a systematic evaluation or author judgment?

### Threat Model Honesty

- [ ] **Phase 1 limitations:** Table 5 (threat model) shows $\times$ for actor impersonation, Byzantine majority, collusion, and social engineering in Phase 1. Is this honest self-assessment sufficient for a security-aware reviewer?
- [ ] **Phase 3 as future work:** The paper says Phase 3 mechanisms (DIDs, signatures, BFT) are "planned" but not implemented. Does this undermine the paper's credibility, or is it acceptable for a systems paper that scopes future work?
- [ ] **E14 collusion vulnerability:** The paper explicitly reports that a single colluding actor can drive $\gamma(C) = 0.99$. This is a "negative result." Is it presented as a structural defect (honest) or as a minor issue (dishonest)? The paper says "structural defect of Phase 1" — this is the correct framing.
- [ ] **E15 defense-in-depth gap:** 4/11 malformed inputs are caught by Pydantic, not preconditions. This reveals that the precondition system is not the first line of defense. Is this a bug or a feature? The paper says "defense-in-depth gap" — is this the right framing?

---

## Known Issues to Flag (Pre-emptive Honesty)

1. **E19 is entirely author-estimated:** Table 8 (E19 benchmark) contains no measured values. The caption says "All values are author estimates." This is honest but may be seen as weak.
2. **E5 is preliminary design only:** The domain-level evaluation (E5) is not executed. The paper says "Status: preliminary design; not yet executed." This is honest but means the paper has no domain-level validation.
3. **Comparative baselines are not run on identical hardware:** Table 7 compares ADL Lite (measured on Apple M2) against nanopubs and PROV-O (published figures, different hardware). This is a limitation acknowledged in the footnote.
4. **Git-only is a straw-man baseline:** Git is not a governance system; comparing it to ADL Lite on governance tasks is unfair. The paper may need to reframe this as "Git-only manual workflow" rather than "Git as a system."
5. **Scale-up projection is extrapolation:** E6b projects to 1M events but admits these are "linear extrapolations, not empirical validations."
6. **Docker image may not build:** The Dockerfile is described but may not have been tested on a clean machine. The LaTeX inclusion adds unnecessary bulk.

---

## Deliverable

Please return a **review report** with:
- **Major issues:** Any experimental design flaw that undermines validity, any performance claim that is false or unsupported, or any reproducibility gap that prevents independent verification.
- **Minor issues:** Missing baselines, suboptimal experimental design, or honest-but-weak claims that could be strengthened.
- **Questions:** Anything that needs clarification from the authors.
- **Verdict:** Accept / Minor revision / Major revision / Reject (with rationale focused on empirical rigor, reproducibility, and threat model honesty).

---

*Generated: 2025-06-16 | Paper version: v0.3.5 (Month 2, Week 7)*
