# Capability: quality-gating

**Status:** validated  
**Confidence:** 0.810  
**Actor:** Coordinator  

## L2 Description

Gate task outputs through quality checks before passing to downstream agents. Enforces minimum confidence thresholds.

## L3 Relations

- `depends-on` -> `logical-consistency-check`
- `depends-on` -> `citation-verification`

## Events

### 1. register
- **Actor:** coordinator
- **Time:** 2025-06-01T09:48:00+00:00
- **Reasoning:** Initial registration by Coordinator
- **Payload:** {"model": "GPT-4o", "role": "Task orchestration and delegation", "l2_description": "Gate task outputs through quality checks before passing to downstream agents. Enforces minimum confidence thresholds.", "l3_relations": [{"predicate": "depends-on", "target": "logical-consistency-check"}, {"predicate": "depends-on", "target": "citation-verification"}]}

### 2. validate
- **Actor:** critic
- **Time:** 2025-06-01T10:57:00+00:00
- **Confidence:** 0.81
- **Reasoning:** Thresholds prevent low-quality propagation
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.81}

### 3. validate
- **Actor:** writer
- **Time:** 2025-06-01T10:59:00+00:00
- **Confidence:** 0.72
- **Reasoning:** Rejection feedback helps
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.72}

### 4. evidence
- **Actor:** coordinator
- **Time:** 2025-06-01T11:26:00+00:00
- **Confidence:** 0.77
- **Reasoning:** 8 outputs gated. 2 rejected, both justified. Precision=1.0.
- **Payload:** {"gated": 8, "rejected": 2, "precision": 1.0, "confidence": 0.77}

