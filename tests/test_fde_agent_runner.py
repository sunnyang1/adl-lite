"""Tests for FDE AgentRunner — fallback mode, LLM mode, structured output parsing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from adl_lite.fde.agent_runner import AgentRunner

# ---------------------------------------------------------------------------
# parse_structured_output
# ---------------------------------------------------------------------------


class TestParseStructuredOutput:
    """Tests for AgentRunner.parse_structured_output."""

    def test_json_code_block_extraction(self):
        raw = 'Some text\n```json\n{"key": "value", "num": 42}\n```\nMore text'
        result = AgentRunner.parse_structured_output(raw, {})
        assert result == {"key": "value", "num": 42}

    def test_plain_json_code_block(self):
        raw = '```\n{"a": 1}\n```'
        result = AgentRunner.parse_structured_output(raw, {})
        assert result == {"a": 1}

    def test_direct_json_parse(self):
        raw = '{"name": "Alice", "age": 30}'
        result = AgentRunner.parse_structured_output(raw, {})
        assert result == {"name": "Alice", "age": 30}

    def test_invalid_json_code_block_falls_back(self):
        raw = "```json\n{invalid json}\n```"
        result = AgentRunner.parse_structured_output(raw, {})
        assert result == {"raw_output": raw}

    def test_invalid_direct_json_falls_back(self):
        raw = "This is not JSON at all"
        result = AgentRunner.parse_structured_output(raw, {})
        assert result == {"raw_output": raw}

    def test_empty_string(self):
        result = AgentRunner.parse_structured_output("", {})
        assert result == {"raw_output": ""}

    def test_json_with_nested_objects(self):
        raw = '```json\n{"outer": {"inner": [1, 2, 3]}}\n```'
        result = AgentRunner.parse_structured_output(raw, {})
        assert result["outer"]["inner"] == [1, 2, 3]

    def test_multiline_json_in_code_block(self):
        raw = '```json\n{\n  "key": "value",\n  "list": [1, 2]\n}\n```'
        result = AgentRunner.parse_structured_output(raw, {})
        assert result == {"key": "value", "list": [1, 2]}


# ---------------------------------------------------------------------------
# _run_fallback_mode
# ---------------------------------------------------------------------------


class TestFallbackMode:
    """Tests for AgentRunner._run_fallback_mode."""

    def test_data_importer_agent_type(self):
        config = {"type": "data_importer", "config": {}}
        data = [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]
        result = AgentRunner._run_fallback_mode(config, data)
        assert result["status"] == "success"
        assert result["metadata"]["mode"] == "rule_engine"
        assert result["metadata"]["provider"] == "fallback"
        assert "columns" in result["output"]

    def test_data_transformer_agent_type(self):
        config = {
            "type": "data_transformer",
            "config": {"transformations": [{"type": "drop", "field": "to_remove"}]},
        }
        data = [{"keep": 1, "to_remove": 2}]
        result = AgentRunner._run_fallback_mode(config, data)
        assert result["status"] == "success"
        assert "to_remove" not in result["output"][0]

    def test_report_generator_agent_type(self):
        config = {"type": "report_generator", "config": {}}
        data = [{"a": 1}, {"a": None}, {"a": None}]
        result = AgentRunner._run_fallback_mode(config, data)
        assert result["status"] == "success"
        assert "classification" in result["output"]
        assert "anomalies_detected" in result["output"]
        assert result["output"]["anomalies_detected"] >= 1

    def test_custom_agent_type(self):
        config = {"type": "custom_agent", "config": {}}
        data = [{"a": 1}]
        result = AgentRunner._run_fallback_mode(config, data)
        assert result["status"] == "success"
        assert "classification" in result["output"]
        assert "anomalies" in result["output"]

    def test_fallback_wraps_non_list_input(self):
        """When input_data is not a list, it should be wrapped."""
        config = {"type": "data_importer", "config": {}}
        result = AgentRunner._run_fallback_mode(config, {"single": "dict"})
        assert result["status"] == "success"
        assert result["output"]["row_count"] == 1

    def test_report_generator_with_anomaly_rules(self):
        config = {
            "type": "report_generator",
            "config": {"anomaly_rules": [{"type": "null_threshold", "threshold": 0.1}]},
        }
        data = [{"a": 1}, {"a": None}, {"a": None}]
        result = AgentRunner._run_fallback_mode(config, data)
        assert result["output"]["anomalies_detected"] >= 1
        assert len(result["output"]["anomaly_details"]) >= 1


# ---------------------------------------------------------------------------
# _run_llm_mode
# ---------------------------------------------------------------------------


class TestLLMMode:
    """Tests for AgentRunner._run_llm_mode (with mock LLM service)."""

    @pytest.mark.asyncio
    async def test_llm_mode_success_without_schema(self):
        """LLM mode without output_schema returns raw_output."""
        mock_llm = MagicMock()
        mock_llm.execute = AsyncMock(
            return_value={
                "result": "The analysis is complete.",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "fallback": False,
                "tokens_used": 150,
                "latency_ms": 200,
            }
        )

        agent_config = {
            "id": "a1",
            "type": "analyzer",
            "name": "TestAgent",
            "config": {"use_llm": True, "llm_provider": "openai", "model": "gpt-4o-mini"},
        }

        result = await AgentRunner._run_llm_mode(agent_config, {"data": "test"}, mock_llm)
        assert result["status"] == "success"
        assert result["output"] == {"raw_output": "The analysis is complete."}
        assert result["metadata"]["mode"] == "llm"
        assert result["metadata"]["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_llm_mode_success_with_schema(self):
        """LLM mode with output_schema parses structured output."""
        mock_llm = MagicMock()
        mock_llm.execute = AsyncMock(
            return_value={
                "result": '```json\n{"category": "fraud", "confidence": 0.95}\n```',
                "provider": "anthropic",
                "model": "claude-3",
                "fallback": False,
                "tokens_used": 100,
                "latency_ms": 150,
            }
        )

        agent_config = {
            "id": "a1",
            "type": "classifier",
            "name": "Classifier",
            "config": {
                "use_llm": True,
                "output_schema": {"category": "str", "confidence": "float"},
            },
        }

        result = await AgentRunner._run_llm_mode(agent_config, "test data", mock_llm)
        assert result["status"] == "success"
        assert result["output"]["category"] == "fraud"
        assert result["output"]["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_llm_mode_falls_back_on_exception(self):
        """When LLM service raises, fallback mode is used."""
        mock_llm = MagicMock()
        mock_llm.execute = AsyncMock(side_effect=Exception("API timeout"))

        agent_config = {
            "id": "a1",
            "type": "data_importer",
            "name": "Agent",
            "config": {"use_llm": True},
        }

        result = await AgentRunner._run_llm_mode(agent_config, [{"a": 1}], mock_llm)
        assert result["status"] == "success"
        assert result["metadata"]["mode"] == "rule_engine"

    @pytest.mark.asyncio
    async def test_llm_mode_string_input_data(self):
        """String input_data is used directly in user_prompt."""
        mock_llm = MagicMock()
        mock_llm.execute = AsyncMock(
            return_value={
                "result": "processed",
                "provider": "test",
                "model": "test-model",
                "fallback": False,
                "tokens_used": 10,
                "latency_ms": 5,
            }
        )

        agent_config = {
            "id": "a1",
            "type": "analyzer",
            "name": "Test",
            "config": {
                "use_llm": True,
                "user_prompt_template": "Analyze: {data}",
            },
        }

        result = await AgentRunner._run_llm_mode(agent_config, "raw text input", mock_llm)
        assert result["status"] == "success"
        # Verify the prompt was constructed with the string
        call_args = mock_llm.execute.call_args
        assert "raw text input" in call_args.kwargs["input_data"]

    @pytest.mark.asyncio
    async def test_llm_mode_dict_input_data(self):
        """Dict input_data is JSON-serialized into the prompt."""
        mock_llm = MagicMock()
        mock_llm.execute = AsyncMock(
            return_value={
                "result": "done",
                "provider": "test",
                "model": "test",
                "fallback": False,
                "tokens_used": 5,
                "latency_ms": 1,
            }
        )

        agent_config = {
            "id": "a1",
            "type": "analyzer",
            "name": "Test",
            "config": {
                "use_llm": True,
                "user_prompt_template": "Data: {data}",
            },
        }

        data = {"key": "value", "num": 42}
        await AgentRunner._run_llm_mode(agent_config, data, mock_llm)
        call_args = mock_llm.execute.call_args
        assert '"key"' in call_args.kwargs["input_data"]

    @pytest.mark.asyncio
    async def test_llm_mode_custom_system_prompt(self):
        """Custom system_prompt is passed to LLM service."""
        mock_llm = MagicMock()
        mock_llm.execute = AsyncMock(
            return_value={
                "result": "ok",
                "provider": "test",
                "model": "test",
                "fallback": False,
                "tokens_used": 1,
                "latency_ms": 1,
            }
        )

        agent_config = {
            "id": "a1",
            "type": "analyzer",
            "name": "Test",
            "config": {
                "use_llm": True,
                "system_prompt": "You are a custom assistant.",
            },
        }

        await AgentRunner._run_llm_mode(agent_config, "data", mock_llm)
        call_args = mock_llm.execute.call_args
        assert call_args.kwargs["agent_config"]["system_prompt"] == "You are a custom assistant."

    @pytest.mark.asyncio
    async def test_llm_mode_default_system_prompt(self):
        """Default system_prompt is generated from agent type and name."""
        mock_llm = MagicMock()
        mock_llm.execute = AsyncMock(
            return_value={
                "result": "ok",
                "provider": "test",
                "model": "test",
                "fallback": False,
                "tokens_used": 1,
                "latency_ms": 1,
            }
        )

        agent_config = {
            "id": "a1",
            "type": "fraud_detector",
            "name": "FraudAgent",
            "config": {"use_llm": True},
        }

        await AgentRunner._run_llm_mode(agent_config, "data", mock_llm)
        call_args = mock_llm.execute.call_args
        system_prompt = call_args.kwargs["agent_config"]["system_prompt"]
        assert "fraud_detector" in system_prompt
        assert "FraudAgent" in system_prompt

    @pytest.mark.asyncio
    async def test_llm_mode_reasoning_content_passed(self):
        """reasoning_content from LLM result is included in metadata."""
        mock_llm = MagicMock()
        mock_llm.execute = AsyncMock(
            return_value={
                "result": "output",
                "provider": "test",
                "model": "test",
                "fallback": False,
                "tokens_used": 10,
                "latency_ms": 50,
                "reasoning_content": "Step-by-step thinking...",
            }
        )

        agent_config = {
            "id": "a1",
            "type": "analyzer",
            "name": "Test",
            "config": {"use_llm": True},
        }

        result = await AgentRunner._run_llm_mode(agent_config, "data", mock_llm)
        assert result["metadata"]["reasoning_content"] == "Step-by-step thinking..."


# ---------------------------------------------------------------------------
# run_agent (entry point)
# ---------------------------------------------------------------------------


class TestRunAgent:
    """Tests for AgentRunner.run_agent dispatch logic."""

    @pytest.mark.asyncio
    async def test_run_agent_fallback_when_no_llm(self):
        """When llm_service is None, fallback mode is used."""
        config = {"type": "data_importer", "config": {}}
        result = await AgentRunner.run_agent(config, [{"a": 1}], llm_service=None)
        assert result["metadata"]["mode"] == "rule_engine"

    @pytest.mark.asyncio
    async def test_run_agent_fallback_when_use_llm_false(self):
        """When use_llm is False, fallback mode is used even with LLM service."""
        config = {"type": "data_importer", "config": {"use_llm": False}}
        mock_llm = MagicMock()
        result = await AgentRunner.run_agent(config, [{"a": 1}], llm_service=mock_llm)
        assert result["metadata"]["mode"] == "rule_engine"

    @pytest.mark.asyncio
    async def test_run_agent_llm_mode_when_enabled(self):
        """When use_llm is True and llm_service is provided, LLM mode is used."""
        mock_llm = MagicMock()
        mock_llm.execute = AsyncMock(
            return_value={
                "result": "llm output",
                "provider": "openai",
                "model": "gpt-4",
                "fallback": False,
                "tokens_used": 50,
                "latency_ms": 100,
            }
        )
        config = {
            "type": "analyzer",
            "name": "Test",
            "config": {"use_llm": True, "llm_provider": "openai", "model": "gpt-4"},
        }
        result = await AgentRunner.run_agent(config, "test data", llm_service=mock_llm)
        assert result["metadata"]["mode"] == "llm"
