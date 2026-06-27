"""Tests for FDE importers — CSV, Excel, API."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from adl_lite.fde.importers.api_importer import APIImporter
from adl_lite.fde.importers.csv_importer import CSVImporter
from adl_lite.fde.importers.excel_importer import ExcelImporter

# ---------------------------------------------------------------------------
# CSVImporter
# ---------------------------------------------------------------------------


class TestCSVImporter:
    """Tests for CSVImporter.import_csv."""

    def test_basic_csv_with_header(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\n")

        result = CSVImporter.import_csv(str(csv_file))
        assert result["headers"] == ["name", "age", "city"]
        assert result["row_count"] == 2
        assert result["data"][0]["name"] == "Alice"
        assert result["data"][0]["age"] == "30"
        assert result["data"][1]["city"] == "Shanghai"

    def test_csv_without_header(self, tmp_path):
        csv_file = tmp_path / "no_header.csv"
        csv_file.write_text("Alice,30\nBob,25\n")

        result = CSVImporter.import_csv(str(csv_file), {"has_header": False})
        assert result["headers"] == ["col_0", "col_1"]
        assert result["row_count"] == 2
        assert result["data"][0]["col_0"] == "Alice"

    def test_csv_max_rows(self, tmp_path):
        csv_file = tmp_path / "large.csv"
        lines = ["name,age"] + [f"Person{i},{i}" for i in range(100)]
        csv_file.write_text("\n".join(lines) + "\n")

        result = CSVImporter.import_csv(str(csv_file), {"max_rows": 11})
        assert result["row_count"] == 10

    def test_csv_custom_delimiter(self, tmp_path):
        csv_file = tmp_path / "semicolon.csv"
        csv_file.write_text("name;age\nAlice;30\n")

        result = CSVImporter.import_csv(str(csv_file), {"delimiter": ";"})
        assert result["headers"] == ["name", "age"]
        assert result["data"][0]["name"] == "Alice"

    def test_empty_csv_file(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")

        result = CSVImporter.import_csv(str(csv_file))
        assert result["headers"] == []
        assert result["data"] == []
        assert result["row_count"] == 0

    def test_csv_only_header_no_data(self, tmp_path):
        csv_file = tmp_path / "header_only.csv"
        csv_file.write_text("name,age\n")

        result = CSVImporter.import_csv(str(csv_file))
        assert result["headers"] == ["name", "age"]
        assert result["row_count"] == 0

    def test_csv_with_short_rows(self, tmp_path):
        """Rows with fewer columns than headers should pad with empty strings."""
        csv_file = tmp_path / "ragged.csv"
        csv_file.write_text("a,b,c\n1,2\n")

        result = CSVImporter.import_csv(str(csv_file))
        assert result["data"][0]["a"] == "1"
        assert result["data"][0]["b"] == "2"
        assert result["data"][0]["c"] == ""

    def test_csv_column_type_inference(self, tmp_path):
        """Column type info should be populated for non-empty data."""
        csv_file = tmp_path / "typed.csv"
        csv_file.write_text("name,age,score\nAlice,30,95.5\nBob,25,87.3\n")

        result = CSVImporter.import_csv(str(csv_file))
        assert len(result["columns"]) == 3
        age_col = [c for c in result["columns"] if c["name"] == "age"][0]
        assert age_col["inferred_type"] == "integer"

    def test_csv_latin1_fallback(self, tmp_path):
        """CSV with non-UTF-8 characters should fall back to latin-1."""
        csv_file = tmp_path / "latin1.csv"
        # Write bytes that are invalid UTF-8 but valid latin-1
        csv_file.write_bytes(b"name,city\nAlice,S\xe3o Paulo\n")

        result = CSVImporter.import_csv(str(csv_file))
        assert result["row_count"] == 1
        assert result["data"][0]["name"] == "Alice"

    def test_csv_default_options(self, tmp_path):
        """Calling with no options should use defaults."""
        csv_file = tmp_path / "default.csv"
        csv_file.write_text("a,b\n1,2\n")

        result = CSVImporter.import_csv(str(csv_file))
        assert result["row_count"] == 1


# ---------------------------------------------------------------------------
# ExcelImporter
# ---------------------------------------------------------------------------


class TestExcelImporter:
    """Tests for ExcelImporter.import_excel."""

    def test_excel_import_requires_openpyxl(self, tmp_path):
        """If openpyxl is not installed, returns error sheet."""
        fake_path = str(tmp_path / "nonexistent.xlsx")
        with patch("builtins.__import__", side_effect=ImportError("No openpyxl")):
            result = ExcelImporter.import_excel(fake_path)
        assert len(result["sheets"]) == 1
        assert "openpyxl" in result["sheets"][0]["error"]

    def test_excel_import_with_mock_workbook(self, tmp_path):
        """Test Excel import with mocked openpyxl workbook."""
        # Create a mock workbook
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = [
            ("name", "age"),
            ("Alice", 30),
            ("Bob", 25),
        ]

        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1"]
        mock_wb.__getitem__ = MagicMock(return_value=mock_ws)

        mock_openpyxl = MagicMock()
        mock_openpyxl.load_workbook = MagicMock(return_value=mock_wb)

        with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
            result = ExcelImporter.import_excel("fake_path.xlsx")

        assert len(result["sheets"]) == 1
        assert result["sheets"][0]["name"] == "Sheet1"
        assert result["sheets"][0]["headers"] == ["name", "age"]
        assert result["sheets"][0]["row_count"] == 2
        assert result["sheets"][0]["data"][0]["name"] == "Alice"

    def test_excel_sheet_not_found(self, tmp_path):
        """Non-existent sheet should return error entry."""
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1", "Sheet2"]

        mock_openpyxl = MagicMock()
        mock_openpyxl.load_workbook = MagicMock(return_value=mock_wb)

        with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
            result = ExcelImporter.import_excel("fake.xlsx", {"sheets": ["NonExistent"]})

        assert result["sheets"][0]["name"] == "NonExistent"
        assert result["sheets"][0]["error"] == "Sheet not found."

    def test_excel_empty_sheet(self, tmp_path):
        """Empty sheet should return zero rows."""
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = []

        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Empty"]
        mock_wb.__getitem__ = MagicMock(return_value=mock_ws)

        mock_openpyxl = MagicMock()
        mock_openpyxl.load_workbook = MagicMock(return_value=mock_wb)

        with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
            result = ExcelImporter.import_excel("fake.xlsx")

        assert result["sheets"][0]["row_count"] == 0
        assert result["sheets"][0]["data"] == []

    def test_excel_without_header(self, tmp_path):
        """has_header=False should auto-generate column names."""
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = [
            ("Alice", 30),
            ("Bob", 25),
        ]

        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1"]
        mock_wb.__getitem__ = MagicMock(return_value=mock_ws)

        mock_openpyxl = MagicMock()
        mock_openpyxl.load_workbook = MagicMock(return_value=mock_wb)

        with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
            result = ExcelImporter.import_excel("fake.xlsx", {"has_header": False})

        assert result["sheets"][0]["headers"] == ["col_0", "col_1"]
        assert result["sheets"][0]["row_count"] == 2

    def test_excel_max_rows(self, tmp_path):
        """max_rows_per_sheet should limit data rows."""
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = [
            ("name", "age"),
            ("Alice", 30),
            ("Bob", 25),
            ("Charlie", 35),
            ("Dave", 40),
        ]

        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1"]
        mock_wb.__getitem__ = MagicMock(return_value=mock_ws)

        mock_openpyxl = MagicMock()
        mock_openpyxl.load_workbook = MagicMock(return_value=mock_wb)

        with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
            result = ExcelImporter.import_excel("fake.xlsx", {"max_rows_per_sheet": 2})

        assert result["sheets"][0]["row_count"] == 2


# ---------------------------------------------------------------------------
# APIImporter
# ---------------------------------------------------------------------------


class TestAPIImporter:
    """Tests for APIImporter.import_api."""

    def test_api_import_requires_httpx(self):
        """If httpx is not installed, returns error dict."""
        with patch("builtins.__import__", side_effect=ImportError("No httpx")):
            result = APIImporter.import_api("https://api.example.com/data")
        assert result["status_code"] == 0
        assert "httpx" in result["data"]["error"]

    def test_api_import_success_with_mock(self):
        """Test API import with mocked httpx client."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.15
        mock_response.json.return_value = {"key": "value"}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request = MagicMock(return_value=mock_response)

        mock_httpx = MagicMock()
        mock_httpx.Client = MagicMock(return_value=mock_client)
        mock_httpx.RequestError = Exception

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = APIImporter.import_api("https://api.example.com/data")

        assert result["status_code"] == 200
        assert result["data"]["key"] == "value"
        assert result["elapsed_ms"] == 150.0

    def test_api_import_with_extract_path(self):
        """extract_path should navigate nested JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_response.json.return_value = {
            "data": {"items": [1, 2, 3]},
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request = MagicMock(return_value=mock_response)

        mock_httpx = MagicMock()
        mock_httpx.Client = MagicMock(return_value=mock_client)
        mock_httpx.RequestError = Exception

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = APIImporter.import_api(
                "https://api.example.com/data",
                options={"extract_path": "data.items"},
            )

        assert result["data"] == [1, 2, 3]

    def test_api_import_non_json_response(self):
        """Non-JSON response should return text."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.01
        mock_response.json.side_effect = json.JSONDecodeError("err", "doc", 0)
        mock_response.text = "Plain text response"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request = MagicMock(return_value=mock_response)

        mock_httpx = MagicMock()
        mock_httpx.Client = MagicMock(return_value=mock_client)
        mock_httpx.RequestError = Exception

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = APIImporter.import_api("https://api.example.com/text")

        assert result["data"] == "Plain text response"

    def test_api_import_post_with_body(self):
        """POST with dict body should send as JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.02
        mock_response.json.return_value = {"created": True}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request = MagicMock(return_value=mock_response)

        mock_httpx = MagicMock()
        mock_httpx.Client = MagicMock(return_value=mock_client)
        mock_httpx.RequestError = Exception

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = APIImporter.import_api(
                "https://api.example.com/create",
                method="POST",
                body={"name": "test"},
            )

        assert result["status_code"] == 201
        call_kwargs = mock_client.request.call_args.kwargs
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["json"] == {"name": "test"}

    def test_api_import_post_with_string_body(self):
        """POST with string body should send as content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.01
        mock_response.json.return_value = {}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request = MagicMock(return_value=mock_response)

        mock_httpx = MagicMock()
        mock_httpx.Client = MagicMock(return_value=mock_client)
        mock_httpx.RequestError = Exception

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            APIImporter.import_api(
                "https://api.example.com/data",
                method="POST",
                body="raw text body",
            )

        call_kwargs = mock_client.request.call_args.kwargs
        assert call_kwargs["content"] == "raw text body"
        assert call_kwargs["json"] is None

    def test_api_import_default_options(self):
        """Default timeout and max_retries should be applied."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.01
        mock_response.json.return_value = {}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request = MagicMock(return_value=mock_response)

        mock_httpx = MagicMock()
        mock_httpx.Client = MagicMock(return_value=mock_client)
        mock_httpx.RequestError = Exception

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            APIImporter.import_api("https://api.example.com/data")

        # Verify httpx.Client was called with default timeout=30.0
        mock_httpx.Client.assert_called_with(timeout=30.0)

    def test_api_import_custom_headers(self):
        """Custom headers should be passed to the request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.01
        mock_response.json.return_value = {}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request = MagicMock(return_value=mock_response)

        mock_httpx = MagicMock()
        mock_httpx.Client = MagicMock(return_value=mock_client)
        mock_httpx.RequestError = Exception

        custom_headers = {"Authorization": "Bearer token123"}
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            APIImporter.import_api(
                "https://api.example.com/data",
                headers=custom_headers,
            )

        call_kwargs = mock_client.request.call_args.kwargs
        assert call_kwargs["headers"] == custom_headers
