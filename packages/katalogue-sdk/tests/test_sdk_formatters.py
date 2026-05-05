"""Tests for katalogue.formatters."""

import csv
import io
import json

import yaml

from katalogue.formatters import (
    format_compact_json,
    format_csv,
    format_descriptions_to_plaintext,
    format_json,
    format_resultset,
    format_yaml,
)

_DRAFTJS = json.dumps(
    {
        "blocks": [
            {"text": "First paragraph", "type": "unstyled"},
            {"text": "Second paragraph", "type": "unstyled"},
        ],
        "entityMap": {},
    }
)


class TestFormatJson:
    def test_returns_valid_json(self):
        data = [{"id": 1, "name": "A"}]
        assert json.loads(format_json(data)) == data

    def test_is_pretty_printed(self):
        output = format_json({"id": 1})
        assert "\n" in output
        assert "  " in output

    def test_non_serializable_uses_str(self):
        from datetime import date

        output = format_json({"d": date(2024, 1, 1)})
        assert "2024-01-01" in output


class TestFormatCompactJson:
    def test_no_whitespace(self):
        output = format_compact_json({"id": 1, "name": "A"})
        assert output == '{"id":1,"name":"A"}'

    def test_returns_valid_json(self):
        data = [{"id": 1}, {"id": 2}]
        assert json.loads(format_compact_json(data)) == data


class TestFormatDescriptionsToPlaintext:
    def test_single_draftjs_string_extracted(self):
        result = format_descriptions_to_plaintext(_DRAFTJS)
        assert result == "First paragraph Second paragraph"

    def test_plain_string_unchanged(self):
        assert format_descriptions_to_plaintext("just text") == "just text"

    def test_non_draftjs_json_unchanged(self):
        raw = json.dumps({"foo": "bar"})
        assert format_descriptions_to_plaintext(raw) == raw

    def test_none_returned_unchanged(self):
        assert format_descriptions_to_plaintext(None) is None

    def test_integer_returned_unchanged(self):
        assert format_descriptions_to_plaintext(42) == 42

    def test_list_of_dicts_applied_recursively(self):
        rows = [{"name": "A", "description": _DRAFTJS}]
        result = format_descriptions_to_plaintext(rows)
        assert result == [
            {"name": "A", "description": "First paragraph Second paragraph"}
        ]

    def test_dict_applied_recursively(self):
        data = {"description": _DRAFTJS, "id": 1}
        result = format_descriptions_to_plaintext(data)
        assert result["description"] == "First paragraph Second paragraph"
        assert result["id"] == 1

    def test_nested_list_in_dict(self):
        data = {"items": [{"desc": _DRAFTJS}]}
        result = format_descriptions_to_plaintext(data)
        assert result["items"][0]["desc"] == "First paragraph Second paragraph"

    def test_empty_blocks_returns_empty_string(self):
        raw = json.dumps({"blocks": [], "entityMap": {}})
        assert format_descriptions_to_plaintext(raw) == ""


_HIERARCHICAL = {
    "resource": "datasource",
    "system": {"system_id": 1, "system_name": "Finance"},
    "datasource": {"datasource_id": 1, "datasource_name": "Sales DB"},
    "datasources": [{"datasource_id": 1, "datasource_name": "Sales DB"}],
    "dataset_groups": [
        {"dataset_group_id": 10, "datasource_id": 1, "dataset_group_name": "public"}
    ],
    "datasets": [
        {"dataset_id": 100, "dataset_group_id": 10, "dataset_name": "customers"},
        {"dataset_id": 101, "dataset_group_id": 10, "dataset_name": "orders"},
    ],
    "fields": [
        {
            "field_id": 1,
            "dataset_id": 100,
            "field_name": "email",
            "dataset_name": "customers",
        },
        {
            "field_id": 2,
            "dataset_id": 101,
            "field_name": "order_id",
            "dataset_name": "orders",
        },
    ],
}


class TestFormatYaml:
    def test_list_serialized_as_yaml(self):
        data = [{"id": 1, "name": "A"}]
        out = format_yaml(data)
        parsed = yaml.safe_load(out)
        assert parsed == data

    def test_dict_serialized_as_yaml(self):
        data = {"key": "value", "num": 42}
        out = format_yaml(data)
        parsed = yaml.safe_load(out)
        assert parsed == data

    def test_output_is_string(self):
        assert isinstance(format_yaml([{"id": 1}]), str)

    def test_unicode_preserved(self):
        data = [{"name": "Åke Söderström"}]
        out = format_yaml(data)
        assert "Åke Söderström" in out


class TestFormatCsv:
    def test_flat_list_produces_csv(self):
        data = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        out = format_csv(data)
        reader = list(csv.DictReader(io.StringIO(out)))
        assert len(reader) == 2
        assert reader[0]["id"] == "1"
        assert reader[0]["name"] == "A"

    def test_empty_list_returns_empty_string(self):
        assert format_csv([]) == ""

    def test_hierarchical_flattens_to_field_level(self):
        out = format_csv(_HIERARCHICAL)
        reader = list(csv.DictReader(io.StringIO(out)))
        assert len(reader) == 2
        field_names = [r["field_name"] for r in reader]
        assert "email" in field_names
        assert "order_id" in field_names

    def test_hierarchical_includes_parent_columns(self):
        out = format_csv(_HIERARCHICAL)
        reader = list(csv.DictReader(io.StringIO(out)))
        row = reader[0]
        assert "datasource_name" in row
        assert row["datasource_name"] == "Sales DB"
        assert "dataset_group_name" in row
        assert row["dataset_group_name"] == "public"

    def test_hierarchical_without_fields_flattens_to_datasets(self):
        data = {**_HIERARCHICAL, "fields": []}
        out = format_csv(data)
        reader = list(csv.DictReader(io.StringIO(out)))
        assert len(reader) == 2
        dataset_names = [r["dataset_name"] for r in reader]
        assert "customers" in dataset_names

    def test_hierarchical_without_fields_or_datasets_flattens_to_dataset_groups(self):
        data = {**_HIERARCHICAL, "fields": [], "datasets": []}
        out = format_csv(data)
        reader = list(csv.DictReader(io.StringIO(out)))
        assert len(reader) == 1
        assert reader[0]["dataset_group_name"] == "public"

    def test_single_dict_produces_one_row(self):
        data = {"datasource_id": 1, "datasource_name": "X"}
        out = format_csv(data)
        reader = list(csv.DictReader(io.StringIO(out)))
        assert len(reader) == 1
        assert reader[0]["datasource_name"] == "X"

    def test_newlines_in_string_values_are_normalized(self):
        data = [{"name": "A", "sql": "SELECT *\nFROM t\nWHERE 1=1"}]
        out = format_csv(data)
        lines = out.splitlines()
        assert len(lines) == 2  # header + 1 data row
        assert "SELECT * FROM t WHERE 1=1" in lines[1]

    def test_crlf_in_string_values_are_normalized(self):
        data = [{"name": "A", "sql": "line1\r\nline2"}]
        out = format_csv(data)
        lines = out.splitlines()
        assert len(lines) == 2
        assert "line1 line2" in lines[1]

    def test_flat_dict_with_inline_fields_is_one_row(self):
        # Regression: a non-hierarchical API response that contains a "fields"
        # key should NOT trigger hierarchical flattening into multiple rows.
        data = {
            "dataset_id": 1,
            "dataset_name": "customers",
            "fields": [{"field_id": 1, "field_name": "email"}],
        }
        out = format_csv(data)
        reader = list(csv.DictReader(io.StringIO(out)))
        assert len(reader) == 1
        assert reader[0]["dataset_name"] == "customers"

    def test_flat_dict_with_inline_datasources_is_one_row(self):
        # Same regression for a response that contains a "datasources" list.
        data = {
            "system_id": 1,
            "system_name": "Finance",
            "datasources": [{"datasource_id": 1}],
        }
        out = format_csv(data)
        reader = list(csv.DictReader(io.StringIO(out)))
        assert len(reader) == 1
        assert reader[0]["system_name"] == "Finance"


class TestFormatResultset:
    def test_fmt_none_returns_python_object(self):
        data = [{"id": 1}]
        result = format_resultset(data, None)
        assert result is data

    def test_fmt_json_returns_string(self):
        data = [{"id": 1}]
        result = format_resultset(data, "json")
        assert isinstance(result, str)
        assert json.loads(result) == data

    def test_fmt_compact_returns_compact_string(self):
        data = [{"id": 1}]
        result = format_resultset(data, "compact")
        assert result == '[{"id":1}]'

    def test_fmt_json_compact_returns_compact_string(self):
        data = [{"id": 1}]
        result = format_resultset(data, "json-compact")
        assert result == '[{"id":1}]'

    def test_fmt_yaml_returns_yaml_string(self):
        data = [{"id": 1}]
        result = format_resultset(data, "yaml")
        assert isinstance(result, str)
        assert yaml.safe_load(result) == data

    def test_fmt_yml_alias_returns_yaml_string(self):
        data = [{"id": 1}]
        result = format_resultset(data, "yml")
        assert isinstance(result, str)
        assert yaml.safe_load(result) == data

    def test_fmt_csv_returns_csv_string(self):
        data = [{"id": 1, "name": "A"}]
        result = format_resultset(data, "csv")
        assert isinstance(result, str)
        assert "id" in result
        assert "name" in result
