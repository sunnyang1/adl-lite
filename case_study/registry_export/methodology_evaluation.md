# Capability: methodology-evaluation

**Status:** validated  
**Confidence:** 0.880  
**Actor:** Analyst  

## L2 Description

Evaluate research methodology quality across 8 dimensions: sample size, controls, statistical rigor, reproducibility, novelty, significance, clarity, and validity.

## L3 Relations

- `depends-on` -> `literature-search`
- `co-occurs-with` -> `statistical-validation`

## Events

### 1. register
- **Actor:** analyst
- **Time:** 2025-06-01T09:09:00+00:00
- **Reasoning:** Initial registration by Analyst
- **Payload:** {"model": "GPT-4o", "role": "Critical analysis of methods and results", "l2_description": "Evaluate research methodology quality across 8 dimensions: sample size, controls, statistical rigor, reproducibility, novelty, significance, clarity, and validity.", "l3_relations": [{"predicate": "depends-on", "target": "literature-search"}, {"predicate": "co-occurs-with", "target": "statistical-validation"}]}

### 2. validate
- **Actor:** critic
- **Time:** 2025-06-01T10:05:00+00:00
- **Confidence:** 0.88
- **Reasoning:** Framework covers validity threats
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.88}

### 3. validate
- **Actor:** coordinator
- **Time:** 2025-06-01T10:07:00+00:00
- **Confidence:** 0.79
- **Reasoning:** Scores correlate with manual assessment
- **Payload:** {"model": "GPT-4o", "confidence": 0.79}

### 4. evidence
- **Actor:** analyst
- **Time:** 2025-06-01T11:05:00+00:00
- **Confidence:** 0.85
- **Reasoning:** Evaluated 25 papers. Cohen kappa=0.71.
- **Payload:** {"papers": 25, "kappa": 0.71, "confidence": 0.85}

### 5. relate
- **Actor:** coordinator
- **Time:** 2025-06-01T11:51:00+00:00
- **Confidence:** 0.88
- **Reasoning:** methodology-evaluation and methodology-critique are complementary: evaluation scores, critique identifies threats.
- **Payload:** {"predicate": "complements", "target": "methodology-critique", "confidence": 0.88}

