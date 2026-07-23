---
adl_type: concept
adl_id: weather-data-retrieval
status: deprecated
confidence: 0.85
scope: public
version: "1.0.0"
actors:
  - agent_1
  - agent_2
  - agent_3
provisional_names:
  zh: "天气数据获取"
  en: "Weather Data Retrieval"
---

# Weather Data Retrieval

## Overview

A tool that fetches weather data from an external API. The capability demonstrates
a full multi-agent lifecycle: registration, validation, dispute, fork, and deprecation.

## Observation

Independent validators tested the v1 endpoint and confirmed the documented
rate limit and error handling, but a later review found the endpoint
outdated: the upstream provider changed authentication requirements,
breaking previously valid integrations.

## Reasoning

Disagreement over the endpoint's validity could not be resolved inside the
original chain — one validator downgraded confidence while another agent
disputed the downgrade. A fork to v2 with the corrected endpoint and
authentication was the cleaner resolution, after which maintaining v1
served no purpose.

## Conclusion

The v1 capability is deprecated in favor of `weather-data-retrieval-v2`.
Consumers should migrate to the v2 endpoint; the chain is retained as the
audit record of the register → validate → dispute → fork → deprecate
lifecycle.

## API Endpoint

- **URL**: `https://api.weather.example.com/v1/current`
- **Method**: GET
- **Rate limit**: 100 requests/minute

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `location` | string | yes | City name or lat,long pair |
| `units` | string | no | `metric` or `imperial` (default: metric) |

## L3: Relations

```adl:relation
source: weather-data-retrieval
relation: co-occurs-with
target: weather-data-retrieval-v2
mapping_type: statistical
confidence: 0.9
```

## L4: Action History

```adl:action
action: register
actor: agent_1
reasoning: "Initial registration of weather data capability"
params:
  endpoint: "https://api.weather.example.com/v1/current"
```

```adl:action
action: validate
actor: agent_2
reasoning: "Endpoint tested; rate limits documented; error handling verified."
params:
  confidence: 0.85
```

```adl:action
action: validate
actor: agent_3
reasoning: "Endpoint outdated; new endpoint requires different authentication."
params:
  confidence: 0.45
```

```adl:action
action: fork
actor: agent_1
reasoning: "Disagree with downgrade; fork to v2 with updated endpoint."
params:
  child_id: weather-data-retrieval-v2
```

```adl:action
action: deprecate
actor: agent_2
reasoning: "Superseded by v2 with corrected endpoint."
```
