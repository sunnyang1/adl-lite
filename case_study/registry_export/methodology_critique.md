# Capability: methodology-critique

**Status:** validated  
**Confidence:** 0.830  
**Actor:** Critic  

## L2 Description

Provide detailed methodology critiques identifying threats to validity and alternative explanations.

## L3 Relations

- `depends-on` -> `methodology-evaluation`

## Events

### 1. register
- **Actor:** critic
- **Time:** 2025-06-01T09:42:00+00:00
- **Reasoning:** Initial registration by Critic
- **Payload:** {"model": "Claude 3.5 Sonnet", "role": "Quality review and fact-checking", "l2_description": "Provide detailed methodology critiques identifying threats to validity and alternative explanations.", "l3_relations": [{"predicate": "depends-on", "target": "methodology-evaluation"}]}

### 2. validate
- **Actor:** analyst
- **Time:** 2025-06-01T10:49:00+00:00
- **Confidence:** 0.83
- **Reasoning:** Aligns with manual review
- **Payload:** {"model": "GPT-4o", "confidence": 0.83}

### 3. validate
- **Actor:** writer
- **Time:** 2025-06-01T10:51:00+00:00
- **Confidence:** 0.69
- **Reasoning:** Appropriate detail for revision
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.69}

### 4. evidence
- **Actor:** critic
- **Time:** 2025-06-01T12:03:00+00:00
- **Confidence:** 0.8
- **Reasoning:** 15 papers. 23 threats, 19 valid. Precision=0.83.
- **Payload:** {"papers": 15, "threats": 23, "precision": 0.83, "confidence": 0.8}

