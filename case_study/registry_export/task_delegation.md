# Capability: task-delegation

**Status:** validated  
**Confidence:** 0.760  
**Actor:** Coordinator  

## L2 Description

Decompose review tasks and delegate to appropriate agents based on capability confidence and availability.

## L3 Relations

- `co-occurs-with` -> `progress-monitoring`

## Events

### 1. register
- **Actor:** coordinator
- **Time:** 2025-06-01T09:45:00+00:00
- **Reasoning:** Initial registration by Coordinator
- **Payload:** {"model": "GPT-4o", "role": "Task orchestration and delegation", "l2_description": "Decompose review tasks and delegate to appropriate agents based on capability confidence and availability.", "l3_relations": [{"predicate": "co-occurs-with", "target": "progress-monitoring"}]}

### 2. validate
- **Actor:** writer
- **Time:** 2025-06-01T10:53:00+00:00
- **Confidence:** 0.76
- **Reasoning:** Assignments match capabilities
- **Payload:** {"model": "Claude 3.5 Sonnet", "confidence": 0.76}

### 3. validate
- **Actor:** analyst
- **Time:** 2025-06-01T10:55:00+00:00
- **Confidence:** 0.74
- **Reasoning:** Balanced workload
- **Payload:** {"model": "GPT-4o", "confidence": 0.74}

### 4. evidence
- **Actor:** coordinator
- **Time:** 2025-06-01T12:05:00+00:00
- **Confidence:** 0.74
- **Reasoning:** 30 tasks, 4 agents. Zero delegation errors.
- **Payload:** {"tasks": 30, "errors": 0, "confidence": 0.74}

