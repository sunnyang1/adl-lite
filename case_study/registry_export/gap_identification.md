# Capability: gap-identification

**Status:** validated  
**Confidence:** 0.740  
**Actor:** Analyst  

## L2 Description

Identify research gaps by analyzing coverage of sub-topics, methodological limitations, and unresolved questions.

## L3 Relations

- `depends-on` -> `methodology-evaluation`
- `co-occurs-with` -> `trend-detection`

## Events

### 1. register
- **Actor:** analyst
- **Time:** 2025-06-01T09:15:00+00:00
- **Reasoning:** Initial registration by Analyst
- **Payload:** {"model": "GPT-4o", "role": "Critical analysis of methods and results", "l2_description": "Identify research gaps by analyzing coverage of sub-topics, methodological limitations, and unresolved questions.", "l3_relations": [{"predicate": "depends-on", "target": "methodology-evaluation"}, {"predicate": "co-occurs-with", "target": "trend-detection"}]}

### 2. validate
- **Actor:** writer
- **Time:** 2025-06-01T10:13:00+00:00
- **Confidence:** 0.74
- **Reasoning:** Gaps align with narrative needs
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.74}

### 3. validate
- **Actor:** coordinator
- **Time:** 2025-06-01T10:15:00+00:00
- **Confidence:** 0.71
- **Reasoning:** Actionable for planning
- **Payload:** {"model": "GPT-4o", "confidence": 0.71}

### 4. evidence
- **Actor:** analyst
- **Time:** 2025-06-01T11:20:00+00:00
- **Confidence:** 0.72
- **Reasoning:** 7 gaps found. 5 novel, 2 already addressed. Precision=0.71.
- **Payload:** {"gaps": 7, "novel": 5, "precision": 0.71, "confidence": 0.72}

