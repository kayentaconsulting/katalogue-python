"""Tests for formatters/output - JSON and table output formatting."""

import json
from pathlib import Path

import pytest

from katalogue.formatters import (
    format_descriptions_to_plaintext as extract_draftjs_text,
)
from katalogue_cli.formatters.output import (
    format_compact_json,
    format_grouped_table,
    format_json,
    format_list_table,
    format_table,
)

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
        from katalogue_cli.formatters.output import format_list_table

        rows = [
            {"id": "sys-001", "name": "CDP", "description": "Customer data"},
            {"id": "sys-002", "name": "PC", "description": "Product catalog"},
        ]
        output = format_list_table(rows)
        assert "id" in output
        assert "name" in output
        assert "description" in output

    def test_renders_row_values(self):
        from katalogue_cli.formatters.output import format_list_table

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
        from katalogue_cli.formatters.output import format_list_table

        output = format_list_table([])
        assert output == "No results."

    def test_handles_null_values(self):
        from katalogue_cli.formatters.output import format_list_table

        rows = [{"id": "sys-001", "name": "CDP", "description": None}]
        output = format_list_table(rows)
        assert "sys-001" in output


_DRAFTJS = json.dumps(
    {
        "blocks": [
            {"text": "This is the OLTP System we use", "type": "unstyled"},
            {"text": "Second paragraph", "type": "unstyled"},
        ],
        "entityMap": {},
    }
)


class TestGroupedTable:
    _single_parent = [("system_id", "system_name")]
    _rows = [
        {
            "system_id": "sys-001",
            "system_name": "CDP",
            "datasource_id": "ds-001",
            "datasource_name": "Orders DB",
        },
        {
            "system_id": "sys-001",
            "system_name": "CDP",
            "datasource_id": "ds-002",
            "datasource_name": "Products DB",
        },
        {
            "system_id": "sys-002",
            "system_name": "Analytics",
            "datasource_id": "ds-003",
            "datasource_name": "Snowflake",
        },
    ]
    _multi_rows = [
        {
            "system_id": "sys-001",
            "system_name": "CDP",
            "datasource_id": "ds-001",
            "datasource_name": "Orders DB",
            "dataset_group_id": "dg-001",
            "dataset_group_name": "Sales",
            "dataset_id": "dt-001",
            "dataset_name": "Orders 2024",
        },
        {
            "system_id": "sys-001",
            "system_name": "CDP",
            "datasource_id": "ds-001",
            "datasource_name": "Orders DB",
            "dataset_group_id": "dg-002",
            "dataset_group_name": "Finance",
            "dataset_id": "dt-002",
            "dataset_name": "Invoices",
        },
    ]

    def test_renders_parent_header(self):
        output = format_grouped_table(self._rows, self._single_parent)
        assert "sys-001" in output
        assert "CDP" in output
        assert "sys-002" in output
        assert "Analytics" in output

    def test_uses_friendly_label_not_field_name(self):
        output = format_grouped_table(self._rows, self._single_parent)
        assert "system:" in output
        assert "system_id:" not in output

    def test_multiple_groups_on_separate_lines(self):
        output = format_grouped_table(self._rows, self._single_parent)
        assert output.count("sys-001") == 1
        assert output.count("sys-002") == 1

    def test_parent_fields_excluded_from_sub_table_columns(self):
        output = format_grouped_table(self._rows, self._single_parent)
        lines = output.splitlines()
        header_lines = [ln for ln in lines if "datasource_id" in ln]
        assert header_lines, "sub-table header not found"
        for h in header_lines:
            assert "system_id" not in h
            assert "system_name" not in h

    def test_child_values_appear_under_correct_group(self):
        output = format_grouped_table(self._rows, self._single_parent)
        idx_002 = output.index("sys-002")
        idx_orders = output.index("Orders DB")
        idx_snowflake = output.index("Snowflake")
        assert idx_orders < idx_002
        assert idx_snowflake > idx_002

    def test_single_group_still_shows_header(self):
        rows = [
            {
                "system_id": "sys-001",
                "system_name": "CDP",
                "datasource_id": "ds-001",
                "datasource_name": "Orders DB",
            }
        ]
        output = format_grouped_table(rows, self._single_parent)
        assert "sys-001" in output
        assert "Orders DB" in output

    def test_empty_rows(self):
        output = format_grouped_table([], self._single_parent)
        assert "No results" in output

    def test_multi_parent_all_on_one_line(self):
        parents = [
            ("system_id", "system_name"),
            ("datasource_id", "datasource_name"),
            ("dataset_group_id", "dataset_group_name"),
        ]
        output = format_grouped_table(self._multi_rows, parents)
        lines = output.splitlines()
        # Each group (dg-001, dg-002) gets its own header line — both contain sys-001 and ds-001
        header_lines = [ln for ln in lines if "dg-001" in ln]
        assert len(header_lines) == 1, "dg-001 group should be on one line"
        assert "sys-001" in header_lines[0]
        assert "ds-001" in header_lines[0]

    def test_multi_parent_friendly_labels(self):
        parents = [
            ("system_id", "system_name"),
            ("datasource_id", "datasource_name"),
            ("dataset_group_id", "dataset_group_name"),
        ]
        output = format_grouped_table(self._multi_rows, parents)
        lines = output.splitlines()
        header_lines = [ln for ln in lines if "sys-001" in ln]
        assert "system:" in header_lines[0]
        assert "datasource:" in header_lines[0]
        assert "dataset group:" in header_lines[0]

    def test_multi_parent_fields_excluded_from_child_table(self):
        parents = [
            ("system_id", "system_name"),
            ("datasource_id", "datasource_name"),
            ("dataset_group_id", "dataset_group_name"),
        ]
        output = format_grouped_table(self._multi_rows, parents)
        lines = output.splitlines()
        header_lines = [ln for ln in lines if "dataset_id" in ln]
        assert header_lines, "child table header not found"
        for h in header_lines:
            assert "system_id" not in h
            assert "datasource_id" not in h
            assert "dataset_group_id" not in h


class TestListTableTruncation:
    def test_long_value_truncated_with_ellipsis(self):
        long_val = "A" * 80
        rows = [{"name": long_val}]
        output = format_list_table(rows)
        assert "A" * 60 in output
        assert "A" * 61 not in output
        assert "…" in output

    def test_short_value_not_truncated(self):
        rows = [{"name": "short"}]
        output = format_list_table(rows)
        assert "short" in output
        assert "…" not in output

    def test_exactly_60_chars_not_truncated(self):
        val = "B" * 60
        rows = [{"name": val}]
        output = format_list_table(rows)
        assert "…" not in output

    def test_column_header_not_truncated(self):
        rows = [{"name": "x"}]
        output = format_list_table(rows)
        assert "name" in output


class TestExtractDraftjsText:
    def test_single_block(self):
        raw = json.dumps({"blocks": [{"text": "Hello world"}], "entityMap": {}})
        assert extract_draftjs_text(raw) == "Hello world"

    def test_multi_block_joined_with_space(self):
        assert (
            extract_draftjs_text(_DRAFTJS)
            == "This is the OLTP System we use Second paragraph"
        )

    def test_plain_string_unchanged(self):
        assert extract_draftjs_text("just a string") == "just a string"

    def test_non_draftjs_json_unchanged(self):
        raw = json.dumps({"foo": "bar"})
        assert extract_draftjs_text(raw) == raw

    def test_none_returns_none(self):
        assert extract_draftjs_text(None) is None

    def test_empty_blocks(self):
        raw = json.dumps({"blocks": [], "entityMap": {}})
        assert extract_draftjs_text(raw) == ""

    def test_table_renders_plain_text_not_raw_json(self):
        rows = [{"system_id": 1, "description": _DRAFTJS}]
        output = format_list_table(rows)
        assert "This is the OLTP System we use" in output
        assert "entityMap" not in output

    def test_json_format_preserves_raw_draftjs(self):
        data = [{"system_id": 1, "description": _DRAFTJS}]
        output = format_json(data)
        assert "entityMap" in output


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
