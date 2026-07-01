# Capability: trend-detection-v2

**Status:** validated  
**Confidence:** 0.830  
**Actor:** Analyst  

## L2 Description



## Events

### 1. register
- **Actor:** analyst
- **Time:** 2025-06-01T11:36:00+00:00
- **Reasoning:** Forked from trend-detection with 3-year moving average to address conference-spike sensitivity.
- **Payload:** {"parent": "trend-detection", "improvement": "3-year MA"}

### 2. validate
- **Actor:** critic
- **Time:** 2025-06-01T11:39:00+00:00
- **Confidence:** 0.83
- **Reasoning:** 3-year MA eliminates false reversals. 0 false reversals, 4/5 genuine trends detected.
- **Payload:** {"false_reversals": 0, "detected": 4, "window": "3-year", "confidence": 0.83}

