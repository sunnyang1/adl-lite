# Capability: citation-verification

**Status:** validated  
**Confidence:** 0.790  
**Actor:** Critic  

## L2 Description

Verify that cited papers actually support the claims made. Cross-references citation context with paper content.

## L3 Relations

- `depends-on` -> `reference-management`
- `depends-on` -> `literature-search`

## Events

### 1. register
- **Actor:** critic
- **Time:** 2025-06-01T09:36:00+00:00
- **Reasoning:** Initial registration by Critic
- **Payload:** {"model": "Claude 3.5 Sonnet", "role": "Quality review and fact-checking", "l2_description": "Verify that cited papers actually support the claims made. Cross-references citation context with paper content.", "l3_relations": [{"predicate": "depends-on", "target": "reference-management"}, {"predicate": "depends-on", "target": "literature-search"}]}

### 2. validate
- **Actor:** scout
- **Time:** 2025-06-01T10:41:00+00:00
- **Confidence:** 0.79
- **Reasoning:** Verified 92% of citations
- **Payload:** {"model": "GPT-4o", "confidence": 0.79}

### 3. validate
- **Actor:** analyst
- **Time:** 2025-06-01T10:43:00+00:00
- **Confidence:** 0.76
- **Reasoning:** Caught 3 misattributed claims
- **Payload:** {"model": "GPT-4o", "confidence": 0.76}

### 4. evidence
- **Actor:** critic
- **Time:** 2025-06-01T11:11:00+00:00
- **Confidence:** 0.82
- **Reasoning:** 143 citations checked. 8 misattributions (5.6%). TP=0.94.
- **Payload:** {"citations": 143, "errors": 8, "tp": 0.94, "confidence": 0.82}

