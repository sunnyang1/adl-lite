# Related Work (draft)

ADL Lite sits at the intersection of multi-agent collaboration, lightweight knowledge structuring, and retrieval over mixed structured-unstructured corpora. It targets stronger semantic anchoring than plain Markdown with lower overhead than ontology-first systems.

## 1. Agent discovery and multi-agent knowledge coordination

Recent multi-agent systems have improved planning, tool use, and division of labor, but many deployments still exchange discoveries as conversational text or loosely formatted notes. This creates recurring coordination problems: unstable referents, implicit scope assumptions, and weak provenance for why a concept was accepted, forked, or deprecated.

ADL Lite contributes at this document-contract layer. Instead of proposing a new runtime, it standardizes what a discovery artifact must contain so heterogeneous agents can parse, validate, and transition the same object.

## 2. Structured knowledge in Markdown: front matter, wiki links, and relation blocks

Markdown with YAML front matter is now common in static-site systems and technical knowledge bases. Front matter gives lightweight metadata without abandoning human-readable authoring. Wiki links similarly provide graph affordances in prose-centric documents. ADL Lite builds directly on these conventions.

The key extension is typed L3 blocks (`adl:relation`, `adl:evidence`, `adl:seal`) that formalize semantics usually left implicit in natural language. This mirrors RDF-like subject-predicate-object modeling at an author-editable level, without requiring full triple-store infrastructure.

By preserving normal Markdown ergonomics, ADL Lite reduces migration friction while still enabling deterministic parsing and validation.

## 3. Retrieval over structured versus plain text

Retrieval literature shows that explicit structure can improve ranking when queries target relational information that plain lexical overlap under-represents. At the same time, structure-aware methods may offer limited gains on straightforward scenario queries already well served by lexical retrieval.

The ADL Lite retrieval findings in Phase B follow this pattern. Under fair-plain comparisons, scenario-only subsets show small or near-zero hit-recall deltas, while L3-only opaque-anchor subsets account for most of the headline gap.

ADL Lite therefore does not claim that structure always dominates plain text retrieval; it supports the narrower claim that typed relational anchors matter most for relation-sensitive probes.

## 4. AML typology and transaction monitoring context

In anti-money-laundering (AML) and transaction monitoring domains, practitioners rely on typology-driven reasoning that is often documented in narrative reports and analyst notes. This creates a recurring challenge for automation: high-value insights may exist in text but remain difficult to query, compare, and lifecycle-manage.

ADL Lite is not an AML detection model and does not replace statistical monitoring pipelines. Its role is representational: to encode discovered patterns, evidence pointers, and relation links in a form that both humans and agents can process consistently.

By evaluating on an AML-oriented mini corpus, ADL Lite treats domain specificity as a stress test for document semantics rather than a claim of production-grade compliance performance.

## 5. Positioning: plain Markdown versus heavy ontologies

A useful way to locate ADL Lite is on a spectrum:

- At one end, **plain Markdown** maximizes author freedom but leaves semantics, lifecycle, and access policy mostly implicit.
- At the other, **heavy ontology stacks** maximize formal expressiveness and inferencing potential but often impose high modeling and infrastructure costs.

ADL Lite occupies a middle position with three practical commitments.

First, it remains **Markdown-native**. Authors do not leave familiar tooling; they add constrained metadata and typed blocks to ordinary documents.

Second, it enforces **minimal semantic discipline** through validators: scoped identifiers, status transitions, relation slot checks, and pronoun-policy constraints for referent clarity. This is stronger than best-effort conventions, but still lighter than full ontology governance.

Third, it supports **incremental retrieval enhancement**. Teams can run TF-IDF with relation-aware boosts from L3 today, and optionally layer hybrid embedding scorers later, without redesigning the document format.

This positioning matters for deployment realism. Many teams do not have resources to maintain enterprise knowledge graph stacks, yet still need more than unstructured notes.

## 6. Distinct contribution in context

Relative to prior strands, ADL Lite combines four elements in a single, low-friction artifact contract: (1) tri-layer Markdown representation, (2) SSA-oriented validation with referent and scope constraints, (3) consensus-chain lifecycle logging with fork support, and (4) hybrid memory indexing that integrates relational signal without requiring a heavyweight ontology runtime.

The resulting research proposition is intentionally bounded. ADL Lite argues that coordination benefits can emerge from disciplined document structure before full formal knowledge engineering overhead. This proposition is testable with ambiguity checks, transition traceability, retrieval ablations, and scope-leak probes.
