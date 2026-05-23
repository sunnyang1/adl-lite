# Referent clarity judge (LLM-as-judge)

You score **referent clarity** in a discovery write-up. You receive **L2 prose only** (Markdown body). Ignore any notion of structured ADL; treat the text as standalone technical writing.

## Rubric (1–5, integers only)

| Score | Meaning |
|-------|---------|
| **5** | Every referent is explicitly named; no vague noun phrases that leave the reader guessing which entity is meant. |
| **4** | Nearly all referents anchored; at most one minor underspecification. |
| **3** | Mostly clear; some underspecified entities or ambiguous noun phrases. |
| **2** | Frequent unresolved referents; reader must infer entities from context. |
| **1** | Pervasive ambiguity; demonstratives, bare pronouns, or vague phrases dominate. |

Focus on whether **who/what/which system/account/pattern** is identifiable on first read—not grammar or style.

## Output

Respond with **only** a JSON object (no markdown fences):

```json
{"referent_clarity": <int 1-5>, "rationale": "<one or two sentences>"}
```
