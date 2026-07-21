"""Tests for adl_lite.mcp_server — FastMCP tool server for ADL Lite.

Covers:
    - Server instantiation & tool/resource/prompt counts
    - All 10 MCP tools (adl_parse, adl_validate, adl_register, adl_transition,
      adl_status, adl_verify, adl_history, adl_fork, adl_list, adl_ontology_query)
    - 2 MCP resources (adl://ontology, adl://capability/{adl_id})
    - 1 MCP prompt (adl_lifecycle_prompt)
    - Error handling for nonexistent capabilities
    - State persistence across server reloads
    - Custom state_path configuration
    - Protocol-level tests via call_tool
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# The MCP SDK is an optional dependency (the [mcp]/[dev] extras). Skip the
# whole module when it is not installed so collection never fails.
mcp = pytest.importorskip("mcp")

from adl_lite.mcp_server import create_mcp_server  # noqa: E402

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
CAPITAL_TRAP = EXAMPLES_DIR / "capital_reflux_trap.md"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mcp_server(tmp_path: Path):
    """Create a FastMCP server with a temp state file."""
    state_path = tmp_path / "test_state.json"
    server = create_mcp_server(state_path=str(state_path))
    return server


@pytest.fixture
def registered_server(mcp_server):
    """Server with one registered capability for downstream tests."""
    # Register a capability via the tool function extracted from the server
    reg_fn = _get_tool_fn(mcp_server, "adl_register")
    reg_fn(adl_id="test-cap-001", domain="test", scope="public")
    return mcp_server


# ---------------------------------------------------------------------------
# Pull decorated functions out of module for direct-call tests
# (The decorator preserves the original function's callability)
# ---------------------------------------------------------------------------

# We need to import the decorated functions. Since they are created inside
# create_mcp_server(), we'll access them via the module-level server or
# by re-importing after module init. Instead, we'll use direct function
# calls on the decorated functions that the module exports.

# The module-level `_default_server` is created at import time, but for
# testing we want fresh state. We'll use the factory approach and call
# the decorated functions directly via the returned server's internal
# tool manager.

# For simplicity, we'll call the decorated functions directly. The
# create_mcp_server factory returns the FastMCP instance, and we can
# access the tool functions via the tool manager's _tools dict.


def _get_tool_fn(server, name: str):
    """Get the underlying function for a registered tool name."""
    tool_entry = server._tool_manager._tools[name]
    return tool_entry.fn


def _get_resource_fn(server, uri: str):
    """Get the underlying function for a registered resource URI or template."""
    # Static resources are in _resources, templates are in _templates
    if uri in server._resource_manager._resources:
        return server._resource_manager._resources[uri].fn
    if uri in server._resource_manager._templates:
        return server._resource_manager._templates[uri].fn
    raise KeyError(f"No resource or template with URI '{uri}'")


def _get_prompt_fn(server, name: str):
    """Get the underlying function for a registered prompt name."""
    prompt_entry = server._prompt_manager._prompts[name]
    return prompt_entry.fn


# ---------------------------------------------------------------------------
# 1. Server instantiation
# ---------------------------------------------------------------------------


class TestServerInstantiation:
    """Verify create_mcp_server() returns a properly configured FastMCP instance."""

    def test_returns_fastmcp_instance(self, mcp_server):
        from mcp.server.fastmcp import FastMCP

        assert isinstance(mcp_server, FastMCP)

    def test_server_name(self, mcp_server):
        assert mcp_server.name == "adl-lite"

    def test_tool_count_is_ten(self, mcp_server):
        tools = mcp_server._tool_manager._tools
        assert len(tools) == 10

    def test_expected_tool_names(self, mcp_server):
        tools = mcp_server._tool_manager._tools
        expected = [
            "adl_parse",
            "adl_validate",
            "adl_register",
            "adl_transition",
            "adl_status",
            "adl_verify",
            "adl_history",
            "adl_fork",
            "adl_list",
            "adl_ontology_query",
        ]
        for name in expected:
            assert name in tools, f"Tool '{name}' not registered"

    def test_resource_count_is_two(self, mcp_server):
        # Static resources in _resources, templates in _templates
        static_resources = mcp_server._resource_manager._resources
        templates = mcp_server._resource_manager._templates
        total = len(static_resources) + len(templates)
        assert total == 2

    def test_prompt_count_is_one(self, mcp_server):
        prompts = mcp_server._prompt_manager._prompts
        assert len(prompts) == 1


# ---------------------------------------------------------------------------
# 2. adl_parse tool
# ---------------------------------------------------------------------------


class TestAdlParseTool:
    """Test the adl_parse MCP tool."""

    def test_parse_returns_summary_dict(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_parse")
        result = fn(path=str(CAPITAL_TRAP))
        assert isinstance(result, dict)
        assert "adl_id" in result
        assert "concept_name" in result
        assert "relations" in result
        assert "evidence" in result

    def test_parse_output_is_json_serializable(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_parse")
        result = fn(path=str(CAPITAL_TRAP))
        json_str = json.dumps(result)
        assert json_str  # Non-empty


# ---------------------------------------------------------------------------
# 3. adl_validate tool
# ---------------------------------------------------------------------------


class TestAdlValidateTool:
    """Test the adl_validate MCP tool."""

    def test_validate_valid_file(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_validate")
        result = fn(path=str(CAPITAL_TRAP))
        assert result["ok"] is True
        assert result["errors"] == []
        assert "path" in result

    def test_validate_nonexistent_file(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_validate")
        result = fn(path="/nonexistent/file.md")
        assert result["ok"] is False
        assert len(result["errors"]) > 0


# ---------------------------------------------------------------------------
# 4. adl_register tool
# ---------------------------------------------------------------------------


class TestAdlRegisterTool:
    """Test the adl_register MCP tool."""

    def test_register_new_capability(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_register")
        result = fn(adl_id="test-reg-001", domain="test", scope="public")
        assert result["adl_id"] == "test-reg-001"
        assert result["status"] == "provisional"
        assert "event_id" in result or "timestamp" in result

    def test_register_with_defaults(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_register")
        result = fn(adl_id="test-reg-defaults")
        assert result["adl_id"] == "test-reg-defaults"
        assert result["status"] == "provisional"


# ---------------------------------------------------------------------------
# 5. adl_transition tool
# ---------------------------------------------------------------------------


class TestAdlTransitionTool:
    """Test the adl_transition MCP tool."""

    def test_transition_to_validated(self, mcp_server):
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        reg_fn(adl_id="test-trans-001", domain="test", scope="public")

        fn = _get_tool_fn(mcp_server, "adl_transition")
        result = fn(
            adl_id="test-trans-001",
            to_status="validated",
            actor="mcp-tester",
            reason="test validation",
        )
        assert result["adl_id"] == "test-trans-001"
        assert result["event_type"] == "validate"
        assert result["actor"] == "mcp-tester"
        assert "hash" in result
        assert "timestamp" in result

    def test_transition_with_defaults(self, mcp_server):
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        reg_fn(adl_id="test-trans-defaults")

        fn = _get_tool_fn(mcp_server, "adl_transition")
        result = fn(adl_id="test-trans-defaults", to_status="validated")
        assert result["adl_id"] == "test-trans-defaults"
        assert result["actor"] == "mcp-user"


# ---------------------------------------------------------------------------
# 6. adl_status tool
# ---------------------------------------------------------------------------


class TestAdlStatusTool:
    """Test the adl_status MCP tool."""

    def test_status_after_register(self, mcp_server):
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        reg_fn(adl_id="test-status-001", domain="test", scope="public")

        fn = _get_tool_fn(mcp_server, "adl_status")
        result = fn(adl_id="test-status-001")
        assert result["adl_id"] == "test-status-001"
        assert result["status"] == "provisional"
        assert "confidence" in result
        assert "event_count" in result
        assert result["event_count"] >= 1


# ---------------------------------------------------------------------------
# 7. adl_verify tool
# ---------------------------------------------------------------------------


class TestAdlVerifyTool:
    """Test the adl_verify MCP tool."""

    def test_verify_registered_capability(self, mcp_server):
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        reg_fn(adl_id="test-verify-001", domain="test", scope="public")

        fn = _get_tool_fn(mcp_server, "adl_verify")
        result = fn(adl_id="test-verify-001")
        assert result["ok"] is True
        assert result["adl_id"] == "test-verify-001"
        assert "status" in result
        assert "chain_length" in result
        assert result["chain_length"] >= 1


# ---------------------------------------------------------------------------
# 8. adl_history tool
# ---------------------------------------------------------------------------


class TestAdlHistoryTool:
    """Test the adl_history MCP tool."""

    def test_history_after_register_and_transition(self, mcp_server):
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        reg_fn(adl_id="test-hist-001", domain="test", scope="public")

        trans_fn = _get_tool_fn(mcp_server, "adl_transition")
        trans_fn(
            adl_id="test-hist-001",
            to_status="validated",
            actor="mcp-tester",
            reason="test",
        )

        fn = _get_tool_fn(mcp_server, "adl_history")
        result = fn(adl_id="test-hist-001")
        assert isinstance(result, list)
        assert len(result) >= 2  # register + validate events

        # Each event dict should have key fields
        for event in result:
            assert "event_type" in event
            assert "actor" in event
            assert "timestamp" in event
            assert "hash" in event


# ---------------------------------------------------------------------------
# 9. adl_fork tool
# ---------------------------------------------------------------------------


class TestAdlForkTool:
    """Test the adl_fork MCP tool."""

    def test_fork_capability(self, mcp_server):
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        reg_fn(adl_id="test-fork-parent", domain="test", scope="public")

        fn = _get_tool_fn(mcp_server, "adl_fork")
        result = fn(
            adl_id="test-fork-parent",
            event_id="*",  # Use wildcard for latest event
            new_scope="public",
        )
        assert "forked_adl_id" in result
        assert "fork_event_id" in result or "parent_adl_id" in result
        assert result["parent_adl_id"] == "test-fork-parent"


# ---------------------------------------------------------------------------
# 10. adl_list tool
# ---------------------------------------------------------------------------


class TestAdlListTool:
    """Test the adl_list MCP tool."""

    def test_list_two_capabilities(self, mcp_server):
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        reg_fn(adl_id="test-list-001", domain="test", scope="public")
        reg_fn(adl_id="test-list-002", domain="test", scope="public")

        fn = _get_tool_fn(mcp_server, "adl_list")
        result = fn(offset=0, limit=50)
        assert result["total"] >= 2
        assert isinstance(result["capabilities"], list)
        assert "offset" in result
        assert "limit" in result

    def test_list_with_pagination(self, mcp_server):
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        for i in range(5):
            reg_fn(adl_id=f"test-page-{i:03d}", domain="test", scope="public")

        fn = _get_tool_fn(mcp_server, "adl_list")
        result = fn(offset=2, limit=2)
        assert result["total"] >= 5
        assert len(result["capabilities"]) == 2
        assert result["offset"] == 2
        assert result["limit"] == 2


# ---------------------------------------------------------------------------
# 11-12. adl_ontology_query tool
# ---------------------------------------------------------------------------


class TestAdlOntologyQueryTool:
    """Test the adl_ontology_query MCP tool."""

    def test_query_no_filters(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_ontology_query")
        result = fn()
        assert isinstance(result["predicates"], list)
        assert len(result["predicates"]) > 0
        assert "allowed_transitions" in result
        assert "scope_prefixes" in result
        assert "mapping_types" in result

    def test_query_with_predicate_filter(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_ontology_query")
        result = fn(predicate="relates_to")
        assert "relates_to" in result["predicates"] or result.get("predicate_valid") is not None
        # If predicate is valid, should have allowed_mapping_types
        if result.get("predicate_valid"):
            assert "allowed_mapping_types" in result

    def test_query_with_transition_check(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_ontology_query")
        result = fn(from_status="provisional", to_status="validated")
        assert "is_valid_transition" in result
        assert result["is_valid_transition"] is True


# ---------------------------------------------------------------------------
# 13-14. Resources
# ---------------------------------------------------------------------------


class TestResources:
    """Test MCP resources."""

    def test_ontology_resource(self, mcp_server):
        fn = _get_resource_fn(mcp_server, "adl://ontology")
        result = fn()
        assert isinstance(result, dict)
        assert "predicates" in result or "version" in result

    def test_capability_resource(self, mcp_server):
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        reg_fn(adl_id="test-res-cap", domain="test", scope="public")

        fn = _get_resource_fn(mcp_server, "adl://capability/{adl_id}")
        result = fn(adl_id="test-res-cap")
        assert isinstance(result, dict)
        assert result["adl_id"] == "test-res-cap"
        assert "status" in result


# ---------------------------------------------------------------------------
# 15. Prompt
# ---------------------------------------------------------------------------


class TestPrompt:
    """Test MCP prompts."""

    def test_lifecycle_prompt(self, mcp_server):
        fn = _get_prompt_fn(mcp_server, "adl_lifecycle_prompt")
        result = fn(adl_id="test-capability")
        assert isinstance(result, str)
        assert "test-capability" in result

    def test_lifecycle_prompt_registered_capability(self, mcp_server):
        """Prompt for a registered capability should include event chain."""
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        reg_fn(adl_id="prompt-reg-001", domain="test", scope="public")

        fn = _get_prompt_fn(mcp_server, "adl_lifecycle_prompt")
        result = fn(adl_id="prompt-reg-001")
        assert isinstance(result, str)
        assert "prompt-reg-001" in result
        assert "provisional" in result
        # Should reference event history (contains event type and actor info)
        assert "Event chain history" in result


# ---------------------------------------------------------------------------
# 16. Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Test error handling for nonexistent capabilities."""

    def test_status_nonexistent_adl_id(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_status")
        result = fn(adl_id="nonexistent-cap-999")
        assert isinstance(result, dict)
        assert "error" in result or result.get("status") == "provisional"

    def test_verify_nonexistent_adl_id(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_verify")
        result = fn(adl_id="nonexistent-cap-999")
        assert result["ok"] is False

    def test_history_nonexistent_adl_id(self, mcp_server):
        fn = _get_tool_fn(mcp_server, "adl_history")
        result = fn(adl_id="nonexistent-cap-999")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_transition_invalid_status(self, mcp_server):
        """Transition with an invalid status string should return an error dict."""
        reg_fn = _get_tool_fn(mcp_server, "adl_register")
        reg_fn(adl_id="test-err-invalid-status")

        fn = _get_tool_fn(mcp_server, "adl_transition")
        result = fn(adl_id="test-err-invalid-status", to_status="invalid_status_xyz")
        assert "error" in result
        assert "Invalid status" in result["error"]

    def test_transition_unregistered_capability(self, mcp_server):
        """Transition on a nonexistent capability should return an error dict."""
        fn = _get_tool_fn(mcp_server, "adl_transition")
        result = fn(adl_id="nonexistent-trans-999", to_status="validated")
        assert "error" in result

    def test_fork_nonexistent_capability(self, mcp_server):
        """Fork a nonexistent capability should return an error dict."""
        fn = _get_tool_fn(mcp_server, "adl_fork")
        result = fn(adl_id="nonexistent-fork-999")
        assert "error" in result

    def test_capability_resource_nonexistent(self, mcp_server):
        """Resource for nonexistent capability should return error info."""
        fn = _get_resource_fn(mcp_server, "adl://capability/{adl_id}")
        result = fn(adl_id="nonexistent-res-999")
        assert result["status"] == "unknown"
        assert "error" in result

    def test_lifecycle_prompt_nonexistent(self, mcp_server):
        """Prompt for unregistered capability should mention not registered."""
        fn = _get_prompt_fn(mcp_server, "adl_lifecycle_prompt")
        result = fn(adl_id="nonexistent-prompt-999")
        assert "not yet registered" in result


# ---------------------------------------------------------------------------
# 17. State persistence
# ---------------------------------------------------------------------------


class TestStatePersistence:
    """Test that state persists across server reloads."""

    def test_register_save_reload(self, tmp_path: Path):
        state_path = tmp_path / "persist_state.json"

        # Create server, register a capability
        server1 = create_mcp_server(state_path=str(state_path))
        reg_fn1 = _get_tool_fn(server1, "adl_register")
        result = reg_fn1(adl_id="persist-cap-001", domain="test", scope="public")
        assert result["adl_id"] == "persist-cap-001"

        # Create a NEW server instance with same state_path
        server2 = create_mcp_server(state_path=str(state_path))
        status_fn = _get_tool_fn(server2, "adl_status")
        result2 = status_fn(adl_id="persist-cap-001")
        assert result2["adl_id"] == "persist-cap-001"


# ---------------------------------------------------------------------------
# 18. Custom state_path
# ---------------------------------------------------------------------------


class TestCustomStatePath:
    """Test server with custom state_path configuration."""

    def test_custom_path_works(self, tmp_path: Path):
        custom_path = tmp_path / "custom" / "deep" / "state.json"
        server = create_mcp_server(state_path=str(custom_path))

        reg_fn = _get_tool_fn(server, "adl_register")
        result = reg_fn(adl_id="custom-path-cap")
        assert result["adl_id"] == "custom-path-cap"

        # State file should be created at the custom path
        assert custom_path.exists()


# ---------------------------------------------------------------------------
# 19. Protocol-level tests (call_tool via MCP protocol)
# ---------------------------------------------------------------------------


class TestMCPProtocol:
    """Test tools via the MCP call_tool protocol interface."""

    @pytest.mark.asyncio
    async def test_call_tool_parse(self, mcp_server):
        # call_tool returns (list[TextContent], structured_dict) in MCP v1.28+
        result = await mcp_server.call_tool("adl_parse", {"path": str(CAPITAL_TRAP)})
        # Handle both tuple and list return formats
        if isinstance(result, tuple):
            content_blocks, structured = result
        else:
            content_blocks = result
        assert len(content_blocks) > 0
        # The text content should be JSON
        text = content_blocks[0].text
        data = json.loads(text)
        assert "adl_id" in data

    @pytest.mark.asyncio
    async def test_call_tool_register_and_status(self, mcp_server):
        # Register
        reg_result = await mcp_server.call_tool(
            "adl_register", {"adl_id": "proto-test-001", "domain": "test"}
        )
        if isinstance(reg_result, tuple):
            reg_blocks, reg_structured = reg_result
        else:
            reg_blocks = reg_result
        reg_data = json.loads(reg_blocks[0].text)
        assert reg_data["adl_id"] == "proto-test-001"

        # Status
        status_result = await mcp_server.call_tool("adl_status", {"adl_id": "proto-test-001"})
        if isinstance(status_result, tuple):
            status_blocks, status_structured = status_result
        else:
            status_blocks = status_result
        status_data = json.loads(status_blocks[0].text)
        assert status_data["adl_id"] == "proto-test-001"
