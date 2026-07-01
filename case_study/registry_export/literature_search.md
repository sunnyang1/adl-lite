# Capability: literature-search

**Status:** validated  
**Confidence:** 0.820  
**Actor:** Scout  

## L2 Description

Search academic databases for papers matching query criteria. Supports arXiv, Semantic Scholar, and Google Scholar.

## L3 Relations

- `co-occurs-with` -> `keyword-extraction`
- `specializes` -> `information-retrieval`

## Events

### 1. register
- **Actor:** scout
- **Time:** 2025-06-01T09:00:00+00:00
- **Reasoning:** Initial registration by Scout
- **Payload:** {"model": "GPT-4o", "role": "Literature search and retrieval", "l2_description": "Search academic databases for papers matching query criteria. Supports arXiv, Semantic Scholar, and Google Scholar.", "l3_relations": [{"predicate": "co-occurs-with", "target": "keyword-extraction"}, {"predicate": "specializes", "target": "information-retrieval"}]}

### 2. validate
- **Actor:** analyst
- **Time:** 2025-06-01T09:53:00+00:00
- **Confidence:** 0.82
- **Reasoning:** Found 47 relevant papers
- **Payload:** {"model": "GPT-4o", "confidence": 0.82}

### 3. validate
- **Actor:** coordinator
- **Time:** 2025-06-01T09:55:00+00:00
- **Confidence:** 0.75
- **Reasoning:** Covers expected databases
- **Payload:** {"model": "GPT-4o", "confidence": 0.75}

### 4. evidence
- **Actor:** scout
- **Time:** 2025-06-01T11:02:00+00:00
- **Confidence:** 0.88
- **Reasoning:** Retrieved 47 papers. P@10=0.90, recall~0.72.
- **Payload:** {"papers": 47, "p_at_10": 0.9, "recall": 0.72, "confidence": 0.88}

### 5. relate
- **Actor:** coordinator
- **Time:** 2025-06-01T11:53:00+00:00
- **Confidence:** 0.85
- **Reasoning:** literature-search feeds into reference-management pipeline.
- **Payload:** {"predicate": "feeds-into", "target": "reference-management", "confidence": 0.85}

