# Capability: overstatement-detection

**Status:** validated  
**Confidence:** 0.660  
**Actor:** Critic  

## L2 Description

Detect overstatements where claims exceed what the evidence supports.

## L3 Relations

- `depends-on` -> `methodology-evaluation`
- `co-occurs-with` -> `logical-consistency-check`

## Events

### 1. register
- **Actor:** critic
- **Time:** 2025-06-01T09:39:00+00:00
- **Reasoning:** Initial registration by Critic
- **Payload:** {"model": "Claude 3.5 Sonnet", "role": "Quality review and fact-checking", "l2_description": "Detect overstatements where claims exceed what the evidence supports.", "l3_relations": [{"predicate": "depends-on", "target": "methodology-evaluation"}, {"predicate": "co-occurs-with", "target": "logical-consistency-check"}]}

### 2. validate
- **Actor:** writer
- **Time:** 2025-06-01T10:45:00+00:00
- **Confidence:** 0.66
- **Reasoning:** Suggestions improved accuracy
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.66}

### 3. validate
- **Actor:** coordinator
- **Time:** 2025-06-01T10:47:00+00:00
- **Confidence:** 0.6
- **Reasoning:** Acceptable detection, needs FP tuning
- **Payload:** {"model": "GPT-4o", "confidence": 0.6}

### 4. evidence
- **Actor:** critic
- **Time:** 2025-06-01T12:07:00+00:00
- **Confidence:** 0.69
- **Reasoning:** 12 sections. 18 flagged: 14TP, 4FP. Recall=0.82.
- **Payload:** {"flagged": 18, "tp": 14, "recall": 0.82, "confidence": 0.69}

