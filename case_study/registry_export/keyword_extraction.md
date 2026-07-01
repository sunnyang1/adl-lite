# Capability: keyword-extraction

**Status:** validated  
**Confidence:** 0.850  
**Actor:** Scout  

## L2 Description

Extract domain-specific keywords from paper abstracts using TF-IDF and RAKE.

## L3 Relations

- `co-occurs-with` -> `literature-search`

## Events

### 1. register
- **Actor:** scout
- **Time:** 2025-06-01T09:06:00+00:00
- **Reasoning:** Initial registration by Scout
- **Payload:** {"model": "GPT-4o", "role": "Literature search and retrieval", "l2_description": "Extract domain-specific keywords from paper abstracts using TF-IDF and RAKE.", "l3_relations": [{"predicate": "co-occurs-with", "target": "literature-search"}]}

### 2. validate
- **Actor:** analyst
- **Time:** 2025-06-01T10:01:00+00:00
- **Confidence:** 0.85
- **Reasoning:** Keywords align with domain
- **Payload:** {"model": "GPT-4o", "confidence": 0.85}

### 3. validate
- **Actor:** writer
- **Time:** 2025-06-01T10:03:00+00:00
- **Confidence:** 0.72
- **Reasoning:** Useful for section organization
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.72}

### 4. evidence
- **Actor:** scout
- **Time:** 2025-06-01T11:57:00+00:00
- **Confidence:** 0.81
- **Reasoning:** 156 keywords from 47 abstracts. Expert kappa=0.78.
- **Payload:** {"keywords": 156, "kappa": 0.78, "confidence": 0.81}

