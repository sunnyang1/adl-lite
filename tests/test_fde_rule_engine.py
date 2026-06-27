"""Tests for FDE RuleEngine — column type inference, classification, anomaly detection, transformation."""

from __future__ import annotations

from adl_lite.fde.rule_engine import RuleEngine

# ---------------------------------------------------------------------------
# _infer_column_type
# ---------------------------------------------------------------------------


class TestInferColumnType:
    """Tests for RuleEngine._infer_column_type."""

    def test_empty_list_returns_string(self):
        assert RuleEngine._infer_column_type([]) == "string"

    def test_all_none_returns_string(self):
        assert RuleEngine._infer_column_type([None, None, None]) == "string"

    def test_all_empty_strings_returns_string(self):
        assert RuleEngine._infer_column_type(["", "", ""]) == "string"

    def test_integer_column(self):
        assert RuleEngine._infer_column_type([1, 2, 3, 4, 5]) == "integer"

    def test_integer_as_strings(self):
        assert RuleEngine._infer_column_type(["1", "2", "3", "4", "5"]) == "integer"

    def test_float_column(self):
        assert RuleEngine._infer_column_type([1.1, 2.2, 3.3, 4.4]) == "float"

    def test_mixed_int_float_column(self):
        assert RuleEngine._infer_column_type([1, 2.5, 3, 4.7, 5]) == "float"

    def test_date_column_iso(self):
        assert (
            RuleEngine._infer_column_type(["2024-01-15", "2024-02-20", "2024-03-25", "2024-04-30"])
            == "date"
        )

    def test_date_column_slash_format(self):
        assert (
            RuleEngine._infer_column_type(["01/15/2024", "02/20/2024", "03/25/2024", "04/30/2024"])
            == "date"
        )

    def test_string_column(self):
        assert RuleEngine._infer_column_type(["alice", "bob", "charlie"]) == "string"

    def test_mixed_mostly_string(self):
        assert RuleEngine._infer_column_type(["alice", "bob", "123", "charlie"]) == "string"

    def test_large_sample_truncated_to_50(self):
        """Inference only uses first 50 non-null values."""
        vals = [str(i) for i in range(100)] + ["text"] * 10
        # 100 integers out of 110 total > 80% => integer
        assert RuleEngine._infer_column_type(vals) == "integer"

    def test_none_values_skipped(self):
        assert (
            RuleEngine._infer_column_type([None, 1, None, 2, None, 3, None, 4, None, 5])
            == "integer"
        )


# ---------------------------------------------------------------------------
# classify_data
# ---------------------------------------------------------------------------


class TestClassifyData:
    """Tests for RuleEngine.classify_data."""

    def test_empty_data(self):
        result = RuleEngine.classify_data([])
        assert result == {"columns": [], "row_count": 0, "summary": {}}

    def test_single_row(self):
        data = [{"name": "Alice", "age": "30"}]
        result = RuleEngine.classify_data(data)
        assert result["row_count"] == 1
        assert result["column_count"] == 2
        assert len(result["columns"]) == 2

    def test_multiple_rows(self):
        data = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
            {"name": "Charlie", "age": "35"},
        ]
        result = RuleEngine.classify_data(data)
        assert result["row_count"] == 3
        assert result["column_count"] == 2
        assert result["summary"]["total_rows"] == 3
        assert result["summary"]["total_columns"] == 2

    def test_column_info_contains_type(self):
        data = [{"age": "30"}, {"age": "25"}]
        result = RuleEngine.classify_data(data)
        age_col = [c for c in result["columns"] if c["name"] == "age"][0]
        assert age_col["inferred_type"] == "integer"
        assert age_col["non_null_count"] == 2
        assert age_col["null_count"] == 0

    def test_null_count_tracked(self):
        data = [
            {"name": "Alice", "email": "a@b.com"},
            {"name": "Bob", "email": ""},
            {"name": "Charlie", "email": None},
        ]
        result = RuleEngine.classify_data(data)
        email_col = [c for c in result["columns"] if c["name"] == "email"][0]
        assert email_col["non_null_count"] == 1
        assert email_col["null_count"] == 2

    def test_uneven_rows(self):
        """Rows with different keys should produce correct column set."""
        data = [{"a": 1}, {"b": 2}, {"a": 3, "b": 4}]
        result = RuleEngine.classify_data(data)
        assert result["column_count"] == 2


# ---------------------------------------------------------------------------
# detect_anomalies
# ---------------------------------------------------------------------------


class TestDetectAnomalies:
    """Tests for RuleEngine.detect_anomalies."""

    def test_empty_data_returns_empty(self):
        assert RuleEngine.detect_anomalies([]) == []

    def test_default_null_threshold_rule(self):
        """Default rule flags columns with > 50% nulls."""
        data = [
            {"a": 1, "b": "x"},
            {"a": None, "b": "y"},
            {"a": None, "b": "z"},
        ]
        anomalies = RuleEngine.detect_anomalies(data)
        assert len(anomalies) == 1
        assert anomalies[0]["column"] == "a"
        assert anomalies[0]["rule"] == "null_threshold"
        assert anomalies[0]["null_ratio"] == 0.667

    def test_custom_null_threshold(self):
        data = [{"a": 1}, {"a": None}, {"a": 2}, {"a": 3}, {"a": 4}]
        # null ratio = 1/5 = 0.2, threshold 0.1 => flagged
        anomalies = RuleEngine.detect_anomalies(
            data, [{"type": "null_threshold", "threshold": 0.1, "columns": ["a"]}]
        )
        assert len(anomalies) == 1
        assert anomalies[0]["column"] == "a"

    def test_null_threshold_high_severity(self):
        """Null ratio > 0.8 => severity 'high'."""
        data = [{"a": 1}, {"a": None}, {"a": None}, {"a": None}, {"a": None}, {"a": None}]
        anomalies = RuleEngine.detect_anomalies(
            data, [{"type": "null_threshold", "threshold": 0.1}]
        )
        assert anomalies[0]["severity"] == "high"

    def test_null_threshold_medium_severity(self):
        """Null ratio between 0.5 and 0.8 => severity 'medium'."""
        data = [{"a": 1}, {"a": None}, {"a": 1}, {"a": None}]
        anomalies = RuleEngine.detect_anomalies(
            data, [{"type": "null_threshold", "threshold": 0.1}]
        )
        assert anomalies[0]["severity"] == "medium"

    def test_outlier_std_detection(self):
        """Values beyond 3 std deviations are flagged."""
        data = [{"v": float(i)} for i in range(100)]
        # Inject an outlier
        data.append({"v": 10000.0})
        anomalies = RuleEngine.detect_anomalies(
            data, [{"type": "outlier_std", "column": "v", "std_factor": 3.0}]
        )
        assert len(anomalies) >= 1
        assert anomalies[0]["column"] == "v"
        assert anomalies[0]["value"] == 10000.0
        assert anomalies[0]["rule"] == "outlier_std"

    def test_outlier_std_no_numeric_values(self):
        data = [{"v": "text"}, {"v": "more text"}]
        anomalies = RuleEngine.detect_anomalies(data, [{"type": "outlier_std", "column": "v"}])
        assert anomalies == []

    def test_outlier_std_zero_std_returns_empty(self):
        """When all values are the same, std=0 => no anomalies."""
        data = [{"v": 5.0}, {"v": 5.0}, {"v": 5.0}]
        anomalies = RuleEngine.detect_anomalies(data, [{"type": "outlier_std", "column": "v"}])
        assert anomalies == []

    def test_outlier_column_not_found(self):
        data = [{"v": 1}]
        anomalies = RuleEngine.detect_anomalies(
            data, [{"type": "outlier_std", "column": "nonexistent"}]
        )
        assert anomalies == []

    def test_null_threshold_specific_columns(self):
        data = [
            {"a": 1, "b": None},
            {"a": 2, "b": None},
        ]
        # Only check column b, not a
        anomalies = RuleEngine.detect_anomalies(
            data, [{"type": "null_threshold", "threshold": 0.5, "columns": ["b"]}]
        )
        assert len(anomalies) == 1
        assert anomalies[0]["column"] == "b"

    def test_unknown_rule_type_ignored(self):
        data = [{"a": 1}]
        anomalies = RuleEngine.detect_anomalies(data, [{"type": "unknown_rule", "threshold": 0.5}])
        assert anomalies == []


# ---------------------------------------------------------------------------
# transform_data
# ---------------------------------------------------------------------------


class TestTransformData:
    """Tests for RuleEngine.transform_data."""

    def test_empty_data(self):
        assert RuleEngine.transform_data([], []) == []

    def test_no_transformations(self):
        data = [{"a": 1}]
        assert RuleEngine.transform_data(data, None) == data

    def test_rename_field(self):
        data = [{"old_name": 1, "other": "x"}]
        result = RuleEngine.transform_data(
            data, [{"type": "rename", "field": "old_name", "new_name": "new_name"}]
        )
        assert "new_name" in result[0]
        assert "old_name" not in result[0]
        assert result[0]["other"] == "x"

    def test_drop_field(self):
        data = [{"a": 1, "b": 2, "c": 3}]
        result = RuleEngine.transform_data(data, [{"type": "drop", "field": "b"}])
        assert "b" not in result[0]
        assert result[0]["a"] == 1
        assert result[0]["c"] == 3

    def test_default_value_for_nulls(self):
        data = [{"a": None}, {"a": ""}, {"a": "existing"}]
        result = RuleEngine.transform_data(
            data, [{"type": "default", "field": "a", "value": "N/A"}]
        )
        assert result[0]["a"] == "N/A"
        assert result[1]["a"] == "N/A"
        assert result[2]["a"] == "existing"

    def test_trim_whitespace(self):
        data = [{"name": "  Alice  "}, {"name": "Bob"}]
        result = RuleEngine.transform_data(data, [{"type": "trim", "field": "name"}])
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"

    def test_trim_non_string_ignored(self):
        data = [{"age": 30}]
        result = RuleEngine.transform_data(data, [{"type": "trim", "field": "age"}])
        assert result[0]["age"] == 30

    def test_multiple_transformations_applied_in_order(self):
        data = [{"old_name": "  Alice  ", "to_drop": 1}]
        result = RuleEngine.transform_data(
            data,
            [
                {"type": "trim", "field": "old_name"},
                {"type": "rename", "field": "old_name", "new_name": "name"},
                {"type": "drop", "field": "to_drop"},
            ],
        )
        assert result[0] == {"name": "Alice"}

    def test_rename_field_not_present(self):
        data = [{"a": 1}]
        result = RuleEngine.transform_data(
            data, [{"type": "rename", "field": "nonexistent", "new_name": "new"}]
        )
        assert result[0] == {"a": 1}

    def test_drop_field_not_present(self):
        data = [{"a": 1}]
        result = RuleEngine.transform_data(data, [{"type": "drop", "field": "nonexistent"}])
        assert result[0] == {"a": 1}

    def test_unknown_transform_type_ignored(self):
        data = [{"a": 1}]
        result = RuleEngine.transform_data(data, [{"type": "unknown", "field": "a"}])
        assert result[0] == {"a": 1}

    def test_original_data_not_mutated(self):
        data = [{"a": 1}]
        original = data[0].copy()
        RuleEngine.transform_data(data, [{"type": "drop", "field": "a"}])
        assert data[0] == original
