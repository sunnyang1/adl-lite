"""Tests for FDE PipelineEngine — DAG execution, node dispatch, validation."""

from __future__ import annotations

import pytest

from adl_lite.fde.pipeline_engine import PipelineEngine

# ---------------------------------------------------------------------------
# validate_pipeline
# ---------------------------------------------------------------------------


class TestValidatePipeline:
    """Tests for PipelineEngine.validate_pipeline."""

    def test_valid_simple_pipeline(self):
        config = {
            "nodes": [
                {"id": "n1", "type": "data_import"},
                {"id": "n2", "type": "transform"},
            ],
            "edges": [{"source": "n1", "target": "n2"}],
        }
        errors = PipelineEngine.validate_pipeline(config)
        assert errors == []

    def test_empty_nodes_error(self):
        config = {"nodes": [], "edges": []}
        errors = PipelineEngine.validate_pipeline(config)
        assert "Pipeline must have at least one node." in errors

    def test_duplicate_node_ids(self):
        config = {
            "nodes": [
                {"id": "n1", "type": "data_import"},
                {"id": "n1", "type": "transform"},
            ],
            "edges": [],
        }
        errors = PipelineEngine.validate_pipeline(config)
        assert "Duplicate node IDs detected." in errors

    def test_invalid_node_type(self):
        config = {
            "nodes": [{"id": "n1", "type": "invalid_type"}],
            "edges": [],
        }
        errors = PipelineEngine.validate_pipeline(config)
        assert any("invalid type" in e for e in errors)

    def test_edge_unknown_source(self):
        config = {
            "nodes": [{"id": "n1", "type": "data_import"}],
            "edges": [{"source": "unknown", "target": "n1"}],
        }
        errors = PipelineEngine.validate_pipeline(config)
        assert any("unknown source" in e for e in errors)

    def test_edge_unknown_target(self):
        config = {
            "nodes": [{"id": "n1", "type": "data_import"}],
            "edges": [{"source": "n1", "target": "unknown"}],
        }
        errors = PipelineEngine.validate_pipeline(config)
        assert any("unknown target" in e for e in errors)

    def test_cycle_detected(self):
        config = {
            "nodes": [
                {"id": "n1", "type": "data_import"},
                {"id": "n2", "type": "transform"},
                {"id": "n3", "type": "export"},
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
                {"source": "n2", "target": "n3"},
                {"source": "n3", "target": "n1"},  # cycle
            ],
        }
        errors = PipelineEngine.validate_pipeline(config)
        assert any("cycle" in e for e in errors)

    def test_no_cycle_in_linear_pipeline(self):
        config = {
            "nodes": [
                {"id": "n1", "type": "data_import"},
                {"id": "n2", "type": "transform"},
                {"id": "n3", "type": "export"},
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
                {"source": "n2", "target": "n3"},
            ],
        }
        errors = PipelineEngine.validate_pipeline(config)
        assert errors == []

    def test_all_valid_node_types(self):
        config = {
            "nodes": [
                {"id": "n1", "type": "data_import"},
                {"id": "n2", "type": "transform"},
                {"id": "n3", "type": "agent"},
                {"id": "n4", "type": "export"},
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
                {"source": "n2", "target": "n3"},
                {"source": "n3", "target": "n4"},
            ],
        }
        errors = PipelineEngine.validate_pipeline(config)
        assert errors == []


# ---------------------------------------------------------------------------
# execute_pipeline
# ---------------------------------------------------------------------------


class TestExecutePipeline:
    """Tests for PipelineEngine.execute_pipeline."""

    def test_empty_pipeline(self):
        result = PipelineEngine.execute_pipeline({"nodes": [], "edges": []}, {})
        assert result["status"] == "empty"

    def test_single_export_node(self):
        config = {
            "nodes": [{"id": "n1", "type": "export", "config": {"format": "json"}}],
            "edges": [],
        }
        result = PipelineEngine.execute_pipeline(config, {})
        assert result["status"] == "completed"
        assert "n1" in result["node_results"]
        assert result["node_results"]["n1"]["status"] == "success"

    def test_linear_pipeline_two_nodes(self):
        config = {
            "nodes": [
                {"id": "n1", "type": "export", "config": {"format": "csv"}},
                {"id": "n2", "type": "export", "config": {"format": "json"}},
            ],
            "edges": [{"source": "n1", "target": "n2"}],
        }
        result = PipelineEngine.execute_pipeline(config, {})
        assert result["status"] == "completed"
        assert result["execution_order"] == ["n1", "n2"]

    def test_parallel_nodes(self):
        """Two independent nodes with no edges between them."""
        config = {
            "nodes": [
                {"id": "n1", "type": "export", "config": {}},
                {"id": "n2", "type": "export", "config": {}},
            ],
            "edges": [],
        }
        result = PipelineEngine.execute_pipeline(config, {})
        assert result["status"] == "completed"
        assert set(result["execution_order"]) == {"n1", "n2"}

    def test_cycle_in_pipeline(self):
        config = {
            "nodes": [
                {"id": "n1", "type": "export"},
                {"id": "n2", "type": "export"},
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
                {"source": "n2", "target": "n1"},
            ],
        }
        result = PipelineEngine.execute_pipeline(config, {})
        assert result["status"] == "error"
        assert "cycle" in result["message"]

    def test_error_stops_execution(self):
        """When a node raises an exception, execution stops."""
        config = {
            "nodes": [
                {"id": "n1", "type": "unknown_type"},
                {"id": "n2", "type": "export", "config": {}},
            ],
            "edges": [{"source": "n1", "target": "n2"}],
        }
        result = PipelineEngine.execute_pipeline(config, {})
        assert result["status"] == "partial"
        assert result["node_results"]["n1"]["status"] == "error"
        # n2 should not have been executed
        assert "n2" not in result["node_results"]

    def test_context_passed_between_nodes(self):
        """previous_output should propagate through pipeline."""
        config = {
            "nodes": [
                {"id": "n1", "type": "export", "config": {"format": "json"}},
                {"id": "n2", "type": "export", "config": {"format": "csv"}},
            ],
            "edges": [{"source": "n1", "target": "n2"}],
        }
        result = PipelineEngine.execute_pipeline(config, {"tenant_id": "t1"})
        assert result["status"] == "completed"

    def test_diamond_dependency(self):
        """Diamond: n1 → n2, n1 → n3, n2 → n4, n3 → n4."""
        config = {
            "nodes": [
                {"id": "n1", "type": "export", "config": {}},
                {"id": "n2", "type": "export", "config": {}},
                {"id": "n3", "type": "export", "config": {}},
                {"id": "n4", "type": "export", "config": {}},
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
                {"source": "n1", "target": "n3"},
                {"source": "n2", "target": "n4"},
                {"source": "n3", "target": "n4"},
            ],
        }
        result = PipelineEngine.execute_pipeline(config, {})
        assert result["status"] == "completed"
        assert result["execution_order"][0] == "n1"
        assert result["execution_order"][-1] == "n4"


# ---------------------------------------------------------------------------
# execute_node
# ---------------------------------------------------------------------------


class TestExecuteNode:
    """Tests for PipelineEngine.execute_node."""

    def test_export_node(self):
        node = {"id": "n1", "type": "export", "config": {"format": "json"}}
        result = PipelineEngine.execute_node(node, {"previous_output": {"key": "val"}})
        assert result["exported"] is True
        assert result["format"] == "json"
        assert result["data_keys"] == ["key"]

    def test_export_node_with_list_data(self):
        node = {"id": "n1", "type": "export", "config": {}}
        result = PipelineEngine.execute_node(node, {"previous_output": [1, 2, 3]})
        assert result["data_keys"] == "list"

    def test_export_node_default_format(self):
        node = {"id": "n1", "type": "export", "config": {}}
        result = PipelineEngine.execute_node(node, {"previous_output": {}})
        assert result["format"] == "json"

    def test_unknown_node_type_raises(self):
        node = {"id": "n1", "type": "nonexistent"}
        with pytest.raises(ValueError, match="Unknown node type"):
            PipelineEngine.execute_node(node, {})

    def test_data_import_csv(self, tmp_path):
        """Test data_import with a real CSV file."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n")

        node = {
            "id": "n1",
            "type": "data_import",
            "config": {"source_type": "csv", "file_path": str(csv_file)},
        }
        result = PipelineEngine.execute_node(node, {})
        assert result["imported"] is True
        assert result["rows"] == 2
        assert "name" in result["headers"]

    def test_data_import_unsupported_source(self):
        node = {
            "id": "n1",
            "type": "data_import",
            "config": {"source_type": "xml", "file_path": "/fake/path"},
        }
        result = PipelineEngine.execute_node(node, {})
        assert result["imported"] is False
        assert "Unsupported" in result["error"]

    def test_transform_with_field_mapping(self):
        node = {
            "id": "n1",
            "type": "transform",
            "config": {"field_mapping": {"old": "new"}},
        }
        context = {"previous_output": [{"old": 1}, {"old": 2}]}
        result = PipelineEngine.execute_node(node, context)
        assert result["transformed"] is True
        assert result["rows"] == 2

    def test_transform_with_type_map(self):
        node = {
            "id": "n1",
            "type": "transform",
            "config": {"type_map": {"age": "int"}},
        }
        context = {"previous_output": [{"age": "30"}, {"age": "25"}]}
        result = PipelineEngine.execute_node(node, context)
        assert result["transformed"] is True

    def test_transform_no_previous_data(self):
        node = {
            "id": "n1",
            "type": "transform",
            "config": {"field_mapping": {"a": "b"}},
        }
        result = PipelineEngine.execute_node(node, {})
        assert result["transformed"] is True
        assert result["rows"] == 0
