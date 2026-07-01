# Capability: abstract-generation-calibrated

**Status:** validated  
**Confidence:** 0.860  
**Actor:** Critic  

## L2 Description



## Events

### 1. register
- **Actor:** critic
- **Time:** 2025-06-01T11:45:00+00:00
- **Reasoning:** Calibrated variant targeting <10% overstatement via evidence-quality hedging.
- **Payload:** {"parent": "abstract-generation", "target_overstatement": 0.1}

### 2. validate
- **Actor:** critic
- **Time:** 2025-06-01T11:48:00+00:00
- **Confidence:** 0.86
- **Reasoning:** Overstatement dropped from 40% to 8%. Quality 3.4->4.1/5.
- **Payload:** {"overstatement": 0.08, "quality": 4.1, "confidence": 0.86}

### 3. validate
- **Actor:** writer
- **Time:** 2025-06-01T11:49:00+00:00
- **Confidence:** 0.78
- **Reasoning:** Accept calibrated version. Evidence-quality hedging is good addition.
- **Payload:** {"position": "accept", "confidence": 0.78}

