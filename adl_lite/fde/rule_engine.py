"""Rule engine — LLM fallback for classification, anomaly detection, and transformation."""

from __future__ import annotations

from typing import Any


class RuleEngine:
    """Predefined rule-based processing for when LLM APIs are unavailable."""

    # ------------------------------------------------------------------
    # Column type inference
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_column_type(values: list[Any]) -> str:
        """Infer the data type of a column from a sample of values."""
        if not values:
            return "string"

        non_none = [v for v in values if v is not None and v != ""]
        if not non_none:
            return "string"

        int_count = 0
        float_count = 0
        date_count = 0

        for val in non_none[:50]:
            s = str(val).strip()
            # Integer check
            try:
                int(s)
                int_count += 1
                continue
            except ValueError:
                pass
            # Float check
            try:
                float(s)
                float_count += 1
                continue
            except ValueError:
                pass
            # Date check (simple ISO format)
            if len(s) >= 10 and (s[4] == "-" or s[2] == "/"):
                date_count += 1
                continue

        total = len(non_none[:50])
        if int_count / total > 0.8:
            return "integer"
        if (int_count + float_count) / total > 0.8:
            return "float"
        if date_count / total > 0.5:
            return "date"
        return "string"

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    @staticmethod
    def classify_data(data: list[dict]) -> dict:
        """
        Classify each column in the data by name and inferred type.

        Returns dict with columns info and summary statistics.
        """
        if not data:
            return {"columns": [], "row_count": 0, "summary": {}}

        columns: dict[str, list[Any]] = {}
        for row in data:
            for key, value in row.items():
                columns.setdefault(key, []).append(value)

        column_info: list[dict] = []
        for col_name, values in columns.items():
            col_type = RuleEngine._infer_column_type(values)
            non_null = sum(1 for v in values if v is not None and v != "")
            column_info.append(
                {
                    "name": col_name,
                    "inferred_type": col_type,
                    "non_null_count": non_null,
                    "null_count": len(values) - non_null,
                }
            )

        return {
            "columns": column_info,
            "row_count": len(data),
            "column_count": len(columns),
            "summary": {"total_rows": len(data), "total_columns": len(columns)},
        }

    # ------------------------------------------------------------------
    # Anomaly detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_anomalies(data: list[dict], rules: list[dict] | None = None) -> list[dict]:
        """
        Detect anomalies in data based on configurable rules.

        Built-in rules:
          - null_threshold: Flag columns where null ratio exceeds threshold.
          - outlier_std: Flag numeric values beyond N standard deviations.

        Args:
            data: List of row dicts.
            rules: Optional list of rule dicts with {type, column, threshold, ...}.

        Returns:
            List of anomaly dicts with {column, row_index, value, rule, severity}.
        """
        anomalies: list[dict] = []
        if not data:
            return anomalies

        rules = rules or [{"type": "null_threshold", "threshold": 0.5}]

        columns: dict[str, list[Any]] = {}
        for row in data:
            for key, value in row.items():
                columns.setdefault(key, []).append(value)

        # Null threshold rule
        for rule in rules:
            if rule.get("type") == "null_threshold":
                threshold = rule.get("threshold", 0.5)
                target_columns = rule.get("columns", list(columns.keys()))
                for col in target_columns:
                    if col not in columns:
                        continue
                    vals = columns[col]
                    null_count = sum(1 for v in vals if v is None or v == "")
                    null_ratio = null_count / len(vals)
                    if null_ratio > threshold:
                        anomalies.append(
                            {
                                "column": col,
                                "rule": "null_threshold",
                                "null_ratio": round(null_ratio, 3),
                                "null_count": null_count,
                                "total_count": len(vals),
                                "severity": "high" if null_ratio > 0.8 else "medium",
                            }
                        )

            elif rule.get("type") == "outlier_std":
                std_factor = rule.get("std_factor", 3.0)
                col = rule.get("column", "")
                if col not in columns:
                    continue
                vals = columns[col]
                numeric_vals: list[float] = []
                for v in vals:
                    try:
                        numeric_vals.append(float(v))
                    except (ValueError, TypeError):
                        pass
                if not numeric_vals:
                    continue
                mean = sum(numeric_vals) / len(numeric_vals)
                variance = sum((x - mean) ** 2 for x in numeric_vals) / len(numeric_vals)
                std = variance**0.5
                if std == 0:
                    continue

                for i, v in enumerate(vals):
                    try:
                        fv = float(v)
                        if abs(fv - mean) > std_factor * std:
                            anomalies.append(
                                {
                                    "column": col,
                                    "row_index": i,
                                    "value": fv,
                                    "mean": round(mean, 3),
                                    "std": round(std, 3),
                                    "rule": "outlier_std",
                                    "severity": "low",
                                }
                            )
                    except (ValueError, TypeError):
                        pass

        return anomalies

    # ------------------------------------------------------------------
    # Transformation
    # ------------------------------------------------------------------

    @staticmethod
    def transform_data(data: list[dict], transformations: list[dict] | None = None) -> list[dict]:
        """
        Apply a sequence of transformations to the data.

        Supported transformation types:
          - rename: {type: "rename", field: old_name, new_name: new_name}
          - drop: {type: "drop", field: name}
          - default: {type: "default", field: name, value: default_value}
          - trim: {type: "trim", field: name}  — strip whitespace

        Args:
            data: List of row dicts.
            transformations: List of transformation rule dicts.

        Returns:
            Transformed list of row dicts.
        """
        if not data or not transformations:
            return data

        transformed: list[dict] = [dict(row) for row in data]

        for tx in transformations:
            tx_type = tx.get("type", "")

            if tx_type == "rename":
                old_name = tx.get("field", "")
                new_name = tx.get("new_name", "")
                for row in transformed:
                    if old_name in row:
                        row[new_name] = row.pop(old_name)

            elif tx_type == "drop":
                field = tx.get("field", "")
                for row in transformed:
                    row.pop(field, None)

            elif tx_type == "default":
                field = tx.get("field", "")
                default_val = tx.get("value", "")
                for row in transformed:
                    if field in row and (row[field] is None or row[field] == ""):
                        row[field] = default_val

            elif tx_type == "trim":
                field = tx.get("field", "")
                for row in transformed:
                    if field in row and isinstance(row[field], str):
                        row[field] = row[field].strip()

        return transformed
