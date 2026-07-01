# Capability: logical-consistency-check

**Status:** validated  
**Confidence:** 0.840  
**Actor:** Critic  

## L2 Description

Verify logical consistency of arguments in generated text. Checks for contradictions, unsupported claims, and logical fallacies.

## L3 Relations

- `depends-on` -> `section-synthesis`

## Events

### 1. register
- **Actor:** critic
- **Time:** 2025-06-01T09:33:00+00:00
- **Reasoning:** Initial registration by Critic
- **Payload:** {"model": "Claude 3.5 Sonnet", "role": "Quality review and fact-checking", "l2_description": "Verify logical consistency of arguments in generated text. Checks for contradictions, unsupported claims, and logical fallacies.", "l3_relations": [{"predicate": "depends-on", "target": "section-synthesis"}]}

### 2. validate
- **Actor:** analyst
- **Time:** 2025-06-01T10:37:00+00:00
- **Confidence:** 0.84
- **Reasoning:** Caught 5 contradictions
- **Payload:** {"model": "GPT-4o", "confidence": 0.84}

### 3. validate
- **Actor:** writer
- **Time:** 2025-06-01T10:39:00+00:00
- **Confidence:** 0.71
- **Reasoning:** Feedback improved revision quality
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.71}

### 4. evidence
- **Actor:** critic
- **Time:** 2025-06-01T11:23:00+00:00
- **Confidence:** 0.81
- **Reasoning:** 12 sections. 5 contradictions, 3 unsupported. FPR=0.08.
- **Payload:** {"sections": 12, "contradictions": 5, "fpr": 0.08, "confidence": 0.81}

