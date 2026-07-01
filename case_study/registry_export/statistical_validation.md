# Capability: statistical-validation

**Status:** validated  
**Confidence:** 0.910  
**Actor:** Analyst  

## L2 Description

Verify statistical claims: check p-values, confidence intervals, effect sizes, and multiple comparison corrections.

## L3 Relations

- `depends-on` -> `methodology-evaluation`

## Events

### 1. register
- **Actor:** analyst
- **Time:** 2025-06-01T09:12:00+00:00
- **Reasoning:** Initial registration by Analyst
- **Payload:** {"model": "GPT-4o", "role": "Critical analysis of methods and results", "l2_description": "Verify statistical claims: check p-values, confidence intervals, effect sizes, and multiple comparison corrections.", "l3_relations": [{"predicate": "depends-on", "target": "methodology-evaluation"}]}

### 2. validate
- **Actor:** critic
- **Time:** 2025-06-01T10:09:00+00:00
- **Confidence:** 0.91
- **Reasoning:** Caught 3 p-hacking papers
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.91}

### 3. validate
- **Actor:** analyst
- **Time:** 2025-06-01T10:11:00+00:00
- **Confidence:** 0.65
- **Reasoning:** Self-validation limited by bias
- **Payload:** {"model": "GPT-4o", "confidence": 0.65}

### 4. evidence
- **Actor:** critic
- **Time:** 2025-06-01T11:29:00+00:00
- **Confidence:** 0.87
- **Reasoning:** 15 papers. 5 flagged, 4 confirmed. Precision=0.80.
- **Payload:** {"papers": 15, "flagged": 5, "confirmed": 4, "precision": 0.8, "confidence": 0.87}

