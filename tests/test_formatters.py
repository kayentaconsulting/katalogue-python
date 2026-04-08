"""Tests for formatters/output - JSON and table output formatting."""

import json
from pathlib import Path

import pytest

from katalogue.formatters.output import format_compact_json, format_json, format_table

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def system_data():
    return json.loads((FIXTURES / "system_export.json").read_text())


class TestJsonFormatter:
    def test_output_is_valid_json(self, system_data):
        output = format_json(system_data)
        parsed = json.loads(output)
        assert parsed == system_data

    def test_output_is_pretty_printed(self, system_data):
        output = format_json(system_data)
        assert "\n" in output
        assert "  " in output  # indented


class TestTableFormatter:
    def test_contains_key_fields(self, system_data):
        output = format_table(system_data)
        # Should contain environment and version from meta
        assert "DEMO" in output
        assert "2.1.0" in output

    def test_handles_empty_data(self):
        output = format_table({"meta": {}, "data": {}})
        assert isinstance(output, str)


class TestListTableFormatter:
    def test_renders_column_headers(self):
        from katalogue.formatters.output import format_list_table

        rows = [
            {"id": "sys-001", "name": "CDP", "description": "Customer data"},
            {"id": "sys-002", "name": "PC", "description": "Product catalog"},
        ]
        output = format_list_table(rows)
        assert "id" in output
        assert "name" in output
        assert "description" in output

    def test_renders_row_values(self):
        from katalogue.formatters.output import format_list_table

        rows = [
            {"id": "sys-001", "name": "CDP"},
            {"id": "sys-002", "name": "PC"},
        ]
        output = format_list_table(rows)
        assert "sys-001" in output
        assert "CDP" in output
        assert "sys-002" in output
        assert "PC" in output

    def test_handles_empty_list(self):
        from katalogue.formatters.output import format_list_table

        output = format_list_table([])
        assert output == "No results."

    def test_handles_null_values(self):
        from katalogue.formatters.output import format_list_table

        rows = [{"id": "sys-001", "name": "CDP", "description": None}]
        output = format_list_table(rows)
        assert "sys-001" in output


class TestCompactJsonFormatter:
    def test_list_is_single_line(self):
        data = [{"system_id": 1, "system_name": "Katalogue"}]
        output = format_compact_json(data)
        assert "\n" not in output

    def test_list_no_spaces(self):
        data = [{"system_id": 1, "system_name": "Katalogue"}]
        output = format_compact_json(data)
        assert output == '[{"system_id":1,"system_name":"Katalogue"}]'

    def test_dict_is_single_line(self):
        data = {"system_id": 1, "system_name": "Katalogue"}
        output = format_compact_json(data)
        assert "\n" not in output
        assert output == '{"system_id":1,"system_name":"Katalogue"}'

    def test_is_valid_json(self):
        import json
        data = [{"system_id": 1}, {"system_id": 2}]
        output = format_compact_json(data)
        assert json.loads(output) == data
