"""CSV importer — reads CSV files and infers column types."""

from __future__ import annotations

import csv
from typing import Any


class CSVImporter:
    """Imports and analyzes data from CSV files."""

    @staticmethod
    def import_csv(file_path: str, options: dict | None = None) -> dict[str, Any]:
        """
        Read a CSV file and return structured data with inferred column types.

        Args:
            file_path: Absolute path to the CSV file.
            options: Optional dict with:
                - delimiter: str (default ',')
                - encoding: str (default 'utf-8')
                - has_header: bool (default True)
                - max_rows: int (default unlimited)

        Returns:
            Dict with keys: headers, data (list of dicts), row_count, columns (type info).
        """
        opts = options or {}
        delimiter = opts.get("delimiter", ",")
        encoding = opts.get("encoding", "utf-8")
        has_header = opts.get("has_header", True)
        max_rows = opts.get("max_rows", 0)

        try:
            with open(file_path, encoding=encoding, newline="") as f:
                reader = csv.reader(f, delimiter=delimiter)
                rows_raw: list[list[str]] = list(reader)

                if max_rows > 0:
                    rows_raw = rows_raw[:max_rows]

        except UnicodeDecodeError:
            with open(file_path, encoding="latin-1", newline="") as f:
                reader = csv.reader(f, delimiter=delimiter)
                rows_raw = list(reader)
                if max_rows > 0:
                    rows_raw = rows_raw[:max_rows]

        if not rows_raw:
            return {"headers": [], "data": [], "row_count": 0, "columns": []}

        if has_header:
            headers = rows_raw[0]
            data_rows = rows_raw[1:]
        else:
            headers = [f"col_{i}" for i in range(len(rows_raw[0]))]
            data_rows = rows_raw

        # Build data as list of dicts
        data: list[dict[str, str]] = []
        for row in data_rows:
            row_dict: dict[str, str] = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else ""
            data.append(row_dict)

        # Infer column types
        columns_info: list[dict] = []
        if data:
            from adl_lite.fde.rule_engine import RuleEngine

            classification = RuleEngine.classify_data(data)
            columns_info = classification.get("columns", [])

        return {
            "headers": headers,
            "data": data,
            "row_count": len(data),
            "columns": columns_info,
        }
