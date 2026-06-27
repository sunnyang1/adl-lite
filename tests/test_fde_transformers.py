"""Tests for FDE FieldMapper — field renaming and type casting."""

from __future__ import annotations

from datetime import datetime

from adl_lite.fde.transformers.field_mapper import FieldMapper

# ---------------------------------------------------------------------------
# map_fields
# ---------------------------------------------------------------------------


class TestMapFields:
    """Tests for FieldMapper.map_fields."""

    def test_basic_rename(self):
        data = [{"old": 1, "keep": "x"}]
        result = FieldMapper.map_fields(data, {"old": "new"})
        assert "new" in result[0]
        assert "old" not in result[0]
        assert result[0]["keep"] == "x"
        assert result[0]["new"] == 1

    def test_multiple_fields_renamed(self):
        data = [{"a": 1, "b": 2, "c": 3}]
        result = FieldMapper.map_fields(data, {"a": "x", "b": "y"})
        assert "x" in result[0]
        assert "y" in result[0]
        assert "c" in result[0]
        assert "a" not in result[0]
        assert "b" not in result[0]

    def test_empty_data(self):
        assert FieldMapper.map_fields([], {"a": "b"}) == []

    def test_empty_mapping(self):
        data = [{"a": 1}]
        result = FieldMapper.map_fields(data, {})
        assert result == data

    def test_none_mapping(self):
        data = [{"a": 1}]
        # Empty dict should return data as-is
        result = FieldMapper.map_fields(data, {})
        assert result == data

    def test_field_not_in_data(self):
        """Mapping for non-existent field should not cause errors."""
        data = [{"a": 1}]
        result = FieldMapper.map_fields(data, {"nonexistent": "new_name"})
        assert result[0] == {"a": 1}

    def test_multiple_rows(self):
        data = [{"old": 1}, {"old": 2}, {"old": 3}]
        result = FieldMapper.map_fields(data, {"old": "new"})
        assert all("new" in row for row in result)
        assert all("old" not in row for row in result)
        assert [r["new"] for r in result] == [1, 2, 3]

    def test_original_data_not_mutated(self):
        data = [{"old": 1}]
        FieldMapper.map_fields(data, {"old": "new"})
        assert data[0] == {"old": 1}


# ---------------------------------------------------------------------------
# cast_types
# ---------------------------------------------------------------------------


class TestCastTypes:
    """Tests for FieldMapper.cast_types."""

    def test_cast_to_int(self):
        data = [{"age": "30"}, {"age": "25"}]
        result = FieldMapper.cast_types(data, {"age": "int"})
        assert result[0]["age"] == 30
        assert result[1]["age"] == 25
        assert isinstance(result[0]["age"], int)

    def test_cast_to_integer(self):
        data = [{"val": "42"}]
        result = FieldMapper.cast_types(data, {"val": "integer"})
        assert result[0]["val"] == 42

    def test_cast_to_float(self):
        data = [{"score": "95.5"}]
        result = FieldMapper.cast_types(data, {"score": "float"})
        assert result[0]["score"] == 95.5
        assert isinstance(result[0]["score"], float)

    def test_cast_to_number(self):
        data = [{"val": "3.14"}]
        result = FieldMapper.cast_types(data, {"val": "number"})
        assert result[0]["val"] == 3.14

    def test_cast_to_str(self):
        data = [{"val": 42}]
        result = FieldMapper.cast_types(data, {"val": "str"})
        assert result[0]["val"] == "42"
        assert isinstance(result[0]["val"], str)

    def test_cast_to_string(self):
        data = [{"val": 42}]
        result = FieldMapper.cast_types(data, {"val": "string"})
        assert result[0]["val"] == "42"

    def test_cast_to_bool_from_string_true(self):
        data = [{"flag": "true"}, {"flag": "yes"}, {"flag": "1"}]
        result = FieldMapper.cast_types(data, {"flag": "bool"})
        assert result[0]["flag"] is True
        assert result[1]["flag"] is True
        assert result[2]["flag"] is True

    def test_cast_to_bool_from_string_false(self):
        data = [{"flag": "false"}, {"flag": "no"}, {"flag": "0"}]
        result = FieldMapper.cast_types(data, {"flag": "boolean"})
        assert result[0]["flag"] is False
        assert result[1]["flag"] is False
        assert result[2]["flag"] is False

    def test_cast_to_bool_from_bool(self):
        data = [{"flag": True}]
        result = FieldMapper.cast_types(data, {"flag": "bool"})
        assert result[0]["flag"] is True

    def test_cast_to_bool_from_int(self):
        data = [{"flag": 1}, {"flag": 0}]
        result = FieldMapper.cast_types(data, {"flag": "bool"})
        assert result[0]["flag"] is True
        assert result[1]["flag"] is False

    def test_cast_to_date_iso_format(self):
        data = [{"date": "2024-01-15"}]
        result = FieldMapper.cast_types(data, {"date": "date"})
        assert result[0]["date"] == "2024-01-15"

    def test_cast_to_date_slash_format(self):
        data = [{"date": "2024/01/15"}]
        result = FieldMapper.cast_types(data, {"date": "date"})
        assert result[0]["date"] == "2024-01-15"

    def test_cast_to_date_us_format(self):
        data = [{"date": "01/15/2024"}]
        result = FieldMapper.cast_types(data, {"date": "date"})
        assert result[0]["date"] == "2024-01-15"

    def test_cast_to_date_from_datetime(self):
        data = [{"date": datetime(2024, 6, 15, 10, 30)}]
        result = FieldMapper.cast_types(data, {"date": "date"})
        assert result[0]["date"] == "2024-06-15"

    def test_cast_int_from_float_string(self):
        """int(float("3.9")) => 3"""
        data = [{"val": "3.9"}]
        result = FieldMapper.cast_types(data, {"val": "int"})
        assert result[0]["val"] == 3

    def test_cast_handles_none_values(self):
        data = [{"val": None}]
        result = FieldMapper.cast_types(data, {"val": "int"})
        assert result[0]["val"] is None

    def test_cast_handles_empty_string(self):
        data = [{"val": ""}]
        result = FieldMapper.cast_types(data, {"val": "int"})
        assert result[0]["val"] is None

    def test_cast_failure_keeps_original(self):
        """When cast fails, original value should be kept."""
        data = [{"val": "not_a_number"}]
        result = FieldMapper.cast_types(data, {"val": "int"})
        assert result[0]["val"] == "not_a_number"

    def test_cast_field_not_in_data(self):
        """Casting a field that doesn't exist should not cause errors."""
        data = [{"a": 1}]
        result = FieldMapper.cast_types(data, {"nonexistent": "int"})
        assert result[0] == {"a": 1}

    def test_cast_multiple_fields(self):
        data = [{"age": "30", "score": "95.5", "name": 42}]
        result = FieldMapper.cast_types(
            data,
            {"age": "int", "score": "float", "name": "str"},
        )
        assert result[0]["age"] == 30
        assert result[0]["score"] == 95.5
        assert result[0]["name"] == "42"

    def test_cast_empty_data(self):
        assert FieldMapper.cast_types([], {"a": "int"}) == []

    def test_cast_empty_type_map(self):
        data = [{"a": 1}]
        result = FieldMapper.cast_types(data, {})
        assert result == data

    def test_cast_date_invalid_format_keeps_original(self):
        """Invalid date format should keep the original value."""
        data = [{"date": "not-a-date"}]
        result = FieldMapper.cast_types(data, {"date": "date"})
        assert result[0]["date"] == "not-a-date"

    def test_cast_str_none_to_none(self):
        """Casting None to string should result in None."""
        data = [{"val": None}]
        result = FieldMapper.cast_types(data, {"val": "str"})
        assert result[0]["val"] is None
