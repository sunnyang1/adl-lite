# Related Work — ADL Lite

Updated 2026-05. Sources: design transcript §6.1, ADL Lite spec, adjacent 2024–2026 literature.

| Area | Representative work | ADL Lite relation | Gap ADL addresses |
|------|---------------------|-------------------|-------------------|
| **Multi-agent memory** | Generative Agents (Park et al.), MemGPT | Long-horizon agent memory | No typed concept consensus or scope URIs |
| **Structured LLM output** | JSON mode, function calling, Pydantic AI | Schema enforcement | Not Markdown-native; poor human edit loop |
| **Wiki / Zettelkasten** | Obsidian, Roam, LLM Wiki patterns | `[[links]]` + YAML | No validation, status machine, or ACL |
| **Knowledge graphs** | Wikidata, Neo4j, GraphRAG | Relation edges | Heavy infra; not agent-authorable in prose |
| **Blockchain consensus** | PoW/PoS chains | Concept Consensus Chain metaphor | Applied to *concept lifecycle*, not currency |
| **Formal methods** | Lean4, Coq, Z3 | `adl:seal` references | ADL stores proof *pointers*, not execution |
| **AML / fraud graphs** | GNN transaction monitoring | AML pilot dataset | Domain eval only; ADL is domain-agnostic |
| **Agent protocols** | MCP, A2A | Optional MCP tools | ADL is document layer beneath tool transport |
| **Semantic anchoring** | SSA (ADL transcript) | Core design | Operationalized in L1/L3 slots + validator |
| **Discovery languages** | Full S-expression ADL (deferred) | Lite Markdown subset | Ecosystem split avoided for v0.1 |

## Positioning statement

ADL Lite occupies the **Markdown-native middle ground**: human-readable like Obsidian, machine-validatable like JSON schemas, and consensus-aware like lightweight event logs — without requiring a graph database or LLM API for Phase 1 reproduction.

## Deferred comparisons (post Phase 1)

- Vector ANN (FAISS) vs graph-only RQ3
- Lean4 seal verification latency
- Full ADL S-expression expressivity tradeoff
