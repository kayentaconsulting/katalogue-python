"""Tests for katalogue.formatters."""

import json


from katalogue.formatters import (
    format_compact_json,
    format_descriptions_to_plaintext,
    format_json,
    format_resultset,
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
