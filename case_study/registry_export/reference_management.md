# Capability: reference-management

**Status:** validated  
**Confidence:** 0.860  
**Actor:** Writer  

## L2 Description

Manage citation formatting, deduplication, and bibliography generation. Supports APA, IEEE, and ACM styles.

## L3 Relations

- `depends-on` -> `literature-search`

## Events

### 1. register
- **Actor:** writer
- **Time:** 2025-06-01T09:30:00+00:00
- **Reasoning:** Initial registration by Writer
- **Payload:** {"model": "Claude 3.5 Sonnet", "role": "Synthesis and writing", "l2_description": "Manage citation formatting, deduplication, and bibliography generation. Supports APA, IEEE, and ACM styles.", "l3_relations": [{"predicate": "depends-on", "target": "literature-search"}]}

### 2. validate
- **Actor:** critic
- **Time:** 2025-06-01T10:33:00+00:00
- **Confidence:** 0.86
- **Reasoning:** Zero formatting errors in 50-paper test
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.86}

### 3. validate
- **Actor:** scout
- **Time:** 2025-06-01T10:35:00+00:00
- **Confidence:** 0.78
- **Reasoning:** Deduplication correctly merges 12 entries
- **Payload:** {"model": "GPT-4o", "confidence": 0.78}

### 4. evidence
- **Actor:** writer
- **Time:** 2025-06-01T12:01:00+00:00
- **Confidence:** 0.84
- **Reasoning:** 143 refs. 12 dups caught. Zero format errors.
- **Payload:** {"refs": 143, "dups": 12, "confidence": 0.84}

