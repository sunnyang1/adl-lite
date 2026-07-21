"""Agent runner — executes agent configurations with LLM or fallback modes."""

from __future__ import annotations

import json
import re
from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)


class AgentRunner:
    """Executes a single agent with either LLM or rule-engine fallback."""

    @staticmethod
    async def run_agent(
        agent_config: dict,
        input_data: Any,
        llm_service: Any | None = None,
    ) -> dict:
        """
        Execute an agent based on its configuration.

        Args:
            agent_config: Dict with keys: id, type, name, config (containing llm_provider, model, etc.).
            input_data: The data to process.
            llm_service: Optional LLMService instance; if None, uses fallback rule engine.

        Returns:
            Dict with keys: status, output, metadata.
        """
        config = agent_config.get("config", {})

        use_llm = config.get("use_llm", False) and llm_service is not None

        if use_llm:
            return await AgentRunner._run_llm_mode(agent_config, input_data, llm_service)
        else:
            return AgentRunner._run_fallback_mode(agent_config, input_data)

    @staticmethod
    async def _run_llm_mode(
        agent_config: dict,
        input_data: Any,
        llm_service: Any,
    ) -> dict:
        """Execute agent in LLM mode: build prompts, call LLM, parse output."""
        config = agent_config.get("config", {})
        system_prompt = config.get(
            "system_prompt",
            f"You are a {agent_config.get('type', 'data analysis')} agent named {agent_config.get('name', 'Agent')}.",
        )
        user_prompt = config.get("user_prompt_template", "Process the following data:\n{data}")
        if isinstance(input_data, str):
            user_prompt = user_prompt.replace("{data}", input_data)
        else:
            user_prompt = user_prompt.replace(
                "{data}", json.dumps(input_data, ensure_ascii=False, indent=2)
            )

        try:
            llm_result = await llm_service.execute(
                agent_config={
                    **agent_config,
                    "llm_provider": config.get("llm_provider", "openai"),
                    "model": config.get("model", "gpt-4o-mini"),
                    "system_prompt": system_prompt,
                },
                input_data=user_prompt,
            )
        except Exception:
            return AgentRunner._run_fallback_mode(agent_config, input_data)

        output_schema = config.get("output_schema", {})
        if output_schema:
            parsed = AgentRunner.parse_structured_output(
                llm_result.get("result", ""), output_schema
            )
        else:
            parsed = {"raw_output": llm_result.get("result", "")}

        return {
            "status": "success",
            "output": parsed,
            "metadata": {
                "mode": "llm",
                "provider": llm_result.get("provider", "unknown"),
                "model": llm_result.get("model", "unknown"),
                "fallback": llm_result.get("fallback", False),
                "tokens_used": llm_result.get("tokens_used", 0),
                "latency_ms": llm_result.get("latency_ms", 0),
                "reasoning_content": llm_result.get("reasoning_content"),
            },
        }

    @staticmethod
    def _run_fallback_mode(agent_config: dict, input_data: Any) -> dict:
        """Execute agent using the rule engine (fallback mode)."""
        from adl_lite.fde.rule_engine import RuleEngine

        agent_type = agent_config.get("type", "custom")
        config = agent_config.get("config", {})

        data = input_data if isinstance(input_data, list) else [input_data]

        result: dict[str, Any] | list[dict[str, Any]] | Any
        if agent_type == "data_importer":
            result = RuleEngine.classify_data(data)
        elif agent_type == "data_transformer":
            result = RuleEngine.transform_data(data, config.get("transformations", []))
        elif agent_type == "report_generator":
            # Report: classify + anomaly detection summary
            classification = RuleEngine.classify_data(data)
            anomalies = RuleEngine.detect_anomalies(data, config.get("anomaly_rules", []))
            result = {
                "classification": classification,
                "anomalies_detected": len(anomalies),
                "anomaly_details": anomalies[:10],
            }
        else:
            # Custom: run all rule engines
            result = {
                "classification": RuleEngine.classify_data(data),
                "anomalies": RuleEngine.detect_anomalies(data, config.get("anomaly_rules", [])),
            }

        return {
            "status": "success",
            "output": result,
            "metadata": {
                "mode": "rule_engine",
                "provider": "fallback",
            },
        }

    @staticmethod
    def parse_structured_output(raw_output: str, output_schema: dict) -> dict:
        """
        Attempt to parse LLM output into a structured format matching output_schema.

        Tries JSON extraction first, then falls back to regex-based key-value parsing.
        """
        # Try JSON block extraction
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
        if json_match:
            try:
                parsed: dict = json.loads(json_match.group(1))
                return parsed
            except json.JSONDecodeError:
                # Fenced block was not valid JSON — fall through to next strategy.
                logger.debug("Fenced JSON block in LLM output failed to parse; trying raw parse")

        # Try direct JSON parse
        try:
            parsed = json.loads(raw_output)
            return parsed  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            # Expected fallback: output is free text, returned wrapped below.
            logger.debug("LLM output is not JSON; falling back to raw_output wrapping")

        # Fallback: return raw output wrapped
        return {"raw_output": raw_output}
