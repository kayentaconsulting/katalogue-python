"""Tests for file_input.load_records — YAML/JSON/CSV parsing."""

from __future__ import annotations

import json

import pytest
import yaml

from katalogue.file_input import load_records


def test_load_yaml_list(tmp_path):
    f = tmp_path / "data.yml"
    f.write_text(yaml.dump([{"business_term_id": 1, "business_term_description": "x"}]))
    result = load_records(str(f))
    assert result == [{"business_term_id": 1, "business_term_description": "x"}]


def test_load_yaml_alias(tmp_path):
    f = tmp_path / "data.yaml"
    f.write_text(yaml.dump([{"glossary_id": 5, "glossary_name": "Finance"}]))
    result = load_records(str(f))
    assert result[0]["glossary_id"] == 5


def test_load_json_list(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(json.dumps([{"business_term_id": 2, "business_term_name": "Revenue"}]))
    result = load_records(str(f))
    assert result == [{"business_term_id": 2, "business_term_name": "Revenue"}]


def test_load_csv(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("business_term_id,business_term_description\n42,New desc\n43,Other\n")
    result = load_records(str(f))
    assert len(result) == 2
    assert result[0]["business_term_id"] == "42"  # CSV values are strings
    assert result[0]["business_term_description"] == "New desc"


def test_unsupported_extension_raises(tmp_path):
    f = tmp_path / "data.xlsx"
    f.write_text("x")
    with pytest.raises(ValueError, match="Unsupported file format"):
        load_records(str(f))


def test_empty_yaml_returns_empty_list(tmp_path):
    f = tmp_path / "data.yml"
    f.write_text("")
    assert load_records(str(f)) == []


def test_empty_json_array_returns_empty_list(tmp_path):
    f = tmp_path / "data.json"
    f.write_text("[]")
    assert load_records(str(f)) == []


def test_empty_csv_returns_empty_list(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("business_term_id,business_term_description\n")
    assert load_records(str(f)) == []


def test_file_not_found_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_records(str(tmp_path / "missing.yml"))


def test_yaml_not_a_list_raises(tmp_path):
    f = tmp_path / "data.yml"
    f.write_text(yaml.dump({"business_term_id": 1}))  # dict, not list
    with pytest.raises(ValueError, match="must contain a list"):
        load_records(str(f))


def test_csv_empty_cell_excluded_from_row(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text(
        "business_term_id,business_term_description,business_term_example\n8,,Test\n"
    )
    result = load_records(str(f))
    assert result == [{"business_term_id": "8", "business_term_example": "Test"}]
    assert "business_term_description" not in result[0]


def test_csv_sparse_rows_independent(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text(
        "business_term_id,business_term_description,business_term_example\n"
        "1,A description,An example\n"
        "2,Another description,\n"
        "3,,Only example\n"
    )
    result = load_records(str(f))
    assert result[0] == {
        "business_term_id": "1",
        "business_term_description": "A description",
        "business_term_example": "An example",
    }
    assert result[1] == {
        "business_term_id": "2",
        "business_term_description": "Another description",
    }
    assert result[2] == {
        "business_term_id": "3",
        "business_term_example": "Only example",
    }


def test_csv_id_only_row_has_no_extra_keys(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("business_term_id,business_term_description\n42,\n")
    result = load_records(str(f))
    assert result == [{"business_term_id": "42"}]


def test_csv_null_sentinel_becomes_none(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("business_term_id,business_term_description\n42,null\n")
    result = load_records(str(f))
    assert result == [{"business_term_id": "42", "business_term_description": None}]


def test_csv_null_sentinel_case_insensitive(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text(
        "business_term_id,business_term_description\n42,NULL\n43,None\n44,none\n"
    )
    result = load_records(str(f))
    assert result[0]["business_term_description"] is None
    assert result[1]["business_term_description"] is None
    assert result[2]["business_term_description"] is None


def test_yaml_none_string_becomes_none(tmp_path):
    f = tmp_path / "data.yml"
    f.write_text("- business_term_id: 42\n  business_term_description: none\n")
    result = load_records(str(f))
    assert result[0]["business_term_description"] is None


def test_yaml_empty_string_becomes_none(tmp_path):
    f = tmp_path / "data.yml"
    f.write_text('- business_term_id: 42\n  business_term_description: ""\n')
    result = load_records(str(f))
    assert result[0]["business_term_description"] is None


def test_json_none_string_becomes_none(tmp_path):
    f = tmp_path / "data.json"
    f.write_text('[{"business_term_id": 42, "business_term_description": "none"}]')
    result = load_records(str(f))
    assert result[0]["business_term_description"] is None


def test_json_empty_string_becomes_none(tmp_path):
    f = tmp_path / "data.json"
    f.write_text('[{"business_term_id": 42, "business_term_description": ""}]')
    result = load_records(str(f))
    assert result[0]["business_term_description"] is None
