"""Pipeline execution engine — DAG-based node execution."""

from __future__ import annotations

import csv
import json
from collections import deque
from pathlib import Path
from typing import Any


class PipelineEngine:
    """Executes pipeline nodes in topological order based on a DAG config."""

    @staticmethod
    def execute_pipeline(pipeline_config: dict, context: dict) -> dict:
        """
        Execute all nodes in a pipeline config following topological order.

        Args:
            pipeline_config: Dict with 'nodes' (list) and 'edges' (list).
            context: Shared context dict passed to each node (e.g. tenant_id, pipeline_id).

        Returns:
            Dict with per-node results keyed by node ID.
        """
        nodes: list[dict] = pipeline_config.get("nodes", [])
        edges: list[dict] = pipeline_config.get("edges", [])

        if not nodes:
            return {"status": "empty", "message": "No nodes to execute."}

        # Build adjacency and in-degree maps
        node_ids = {n["id"] for n in nodes}
        adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
        in_degree: dict[str, int] = dict.fromkeys(node_ids, 0)

        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src in node_ids and tgt in node_ids:
                adjacency[src].append(tgt)
                in_degree[tgt] += 1

        # Topological sort via Kahn's algorithm
        queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
        order: list[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in adjacency.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(nodes):
            return {"status": "error", "message": "Pipeline contains a cycle."}

        # Execute nodes in order
        node_map: dict[str, dict] = {n["id"]: n for n in nodes}
        results: dict[str, Any] = {}
        intermediate_data: Any = None

        for node_id in order:
            node = node_map[node_id]
            try:
                node_result = PipelineEngine.execute_node(
                    node=node,
                    context={**context, "previous_output": intermediate_data},
                )
                results[node_id] = {"status": "success", "output": node_result}
                intermediate_data = node_result
            except Exception as exc:
                results[node_id] = {
                    "status": "error",
                    "node_id": node_id,
                    "node_type": node.get("type", ""),
                    "error": str(exc),
                }
                # Stop execution on error
                break

        return {
            "status": "completed" if len(results) == len(nodes) else "partial",
            "execution_order": order,
            "node_results": results,
        }

    @staticmethod
    def execute_node(node: dict, context: dict) -> dict:
        """
        Execute a single pipeline node based on its type.

        Supported types: data_import, transform, agent, export.
        """
        node_type = node.get("type", "")
        node_config = node.get("config", {})

        if node_type == "data_import":
            return PipelineEngine._execute_data_import(node_config, context)
        elif node_type == "transform":
            return PipelineEngine._execute_transform(node_config, context)
        elif node_type == "agent":
            return PipelineEngine._execute_agent(node_config, context)
        elif node_type == "export":
            return PipelineEngine._execute_export(node_config, context)
        else:
            raise ValueError(
                f"Unknown node type '{node_type}' for node '{node.get('id', 'unknown')}'"
            )

    @staticmethod
    def _execute_data_import(config: dict, context: dict) -> dict:
        """Import data from configured source."""
        source_type = config.get("source_type", "csv")
        file_path = config.get("file_path", "")

        if source_type == "csv" and file_path:
            from adl_lite.fde.importers.csv_importer import CSVImporter

            result = CSVImporter.import_csv(file_path, config.get("options", {}))
            return {
                "imported": True,
                "rows": len(result.get("data", [])),
                "headers": result.get("headers", []),
            }

        elif source_type == "excel" and file_path:
            from adl_lite.fde.importers.excel_importer import ExcelImporter

            result = ExcelImporter.import_excel(file_path, config.get("options", {}))
            return {"imported": True, "sheets": result.get("sheets", [])}

        elif source_type == "api":
            from adl_lite.fde.importers.api_importer import APIImporter

            result = APIImporter.import_api(
                url=config.get("url", ""),
                method=config.get("method", "GET"),
                headers=config.get("headers", {}),
                body=config.get("body"),
                options=config.get("options", {}),
            )
            return {"imported": True, "status_code": result.get("status_code", 0)}

        else:
            return {"imported": False, "error": f"Unsupported source type: {source_type}"}

    @staticmethod
    def _execute_transform(config: dict, context: dict) -> dict:
        """Transform data using field mappings and type casts."""
        data = context.get("previous_output", [])
        mapping = config.get("field_mapping", {})
        type_map = config.get("type_map", {})

        from adl_lite.fde.transformers.field_mapper import FieldMapper

        if mapping:
            data = FieldMapper.map_fields(data, mapping)
        if type_map:
            data = FieldMapper.cast_types(data, type_map)

        return {"transformed": True, "rows": len(data) if isinstance(data, list) else 0}

    @staticmethod
    def _execute_agent(config: dict, context: dict) -> dict:
        """Delegate execution to AgentRunner."""
        from adl_lite.fde.agent_runner import AgentRunner

        result = AgentRunner.run_agent(
            agent_config=config,
            input_data=context.get("previous_output", {}),
            llm_service=None,
        )
        return {"agent_result": result}

    @staticmethod
    def _execute_export(config: dict, context: dict) -> dict:
        """Export pipeline data to a file, or echo its shape when no path is set.

        Config:
            format: "json" (default) or "csv".  CSV requires the data to be a
                list of dict rows; any other payload raises ``ValueError``.
            output_path: Destination file.  Parent directories are created.
                When omitted, the node only reports the payload shape
                (``data_keys``) without writing anything.

        The payload is taken from ``context["previous_output"]``.
        """
        export_format = config.get("format", "json")
        data = context.get("previous_output", {})
        output_path = config.get("output_path", "")

        result: dict[str, Any] = {
            "exported": True,
            "format": export_format,
            "data_keys": list(data.keys()) if isinstance(data, dict) else "list",
        }

        if not output_path:
            return result

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if export_format == "csv":
            if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
                raise ValueError(
                    "CSV export requires previous_output to be a list of dict rows; "
                    f"got {type(data).__name__}"
                )
            fieldnames: list[str] = []
            for row in data:
                for key in row:
                    if key not in fieldnames:
                        fieldnames.append(key)
            with path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
        else:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

        result["output_path"] = str(path)
        result["bytes"] = path.stat().st_size
        return result

    @staticmethod
    def validate_pipeline(pipeline_config: dict) -> list[str]:
        """
        Validate a pipeline configuration.

        Returns a list of error messages (empty if valid).
        """
        errors: list[str] = []
        nodes: list[dict] = pipeline_config.get("nodes", [])
        edges: list[dict] = pipeline_config.get("edges", [])

        if not nodes:
            errors.append("Pipeline must have at least one node.")

        _ids = [n.get("id") for n in nodes]
        node_ids: set[str] = {i for i in _ids if isinstance(i, str)}
        if len(node_ids) != len(nodes):
            errors.append("Duplicate node IDs detected.")

        valid_types = {"data_import", "transform", "agent", "export"}
        for node in nodes:
            ntype = node.get("type", "")
            if ntype not in valid_types:
                errors.append(f"Node '{node.get('id', '?')}' has invalid type: {ntype}")

        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src not in node_ids:
                errors.append(f"Edge references unknown source node: {src}")
            if tgt not in node_ids:
                errors.append(f"Edge references unknown target node: {tgt}")

        # Check for cycles using DFS
        if nodes and edges:
            adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
            for edge in edges:
                src = edge.get("source", "")
                tgt = edge.get("target", "")
                if src in adjacency and tgt in adjacency:
                    adjacency[src].append(tgt)

            def _has_cycle(nid: str, visited: set[str], stack: set[str]) -> bool:
                visited.add(nid)
                stack.add(nid)
                for neighbor in adjacency.get(nid, []):
                    if neighbor not in visited:
                        if _has_cycle(neighbor, visited, stack):
                            return True
                    elif neighbor in stack:
                        return True
                stack.discard(nid)
                return False

            visited: set[str] = set()
            for nid in node_ids:
                if nid not in visited:
                    if _has_cycle(nid, visited, set()):
                        errors.append("Pipeline contains a cycle.")
                        break

        return errors
