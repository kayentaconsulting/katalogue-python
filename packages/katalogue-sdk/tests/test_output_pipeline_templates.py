"""Tests for OutputPipeline — template rendering path."""

import json

import pytest
import yaml

from katalogue.options import OutputOptions
from katalogue.output import OutputPipeline

_FLAT = {
    "resource": "datasource",
    "id": "1",
    "system": {"system_id": 1, "system_name": "Finance"},
    "datasource": {"datasource_id": 1, "datasource_name": "Sales DB"},
    "dataset_groups": [
        {"dataset_group_id": 1, "datasource_id": 1, "dataset_group_name": "public"},
    ],
    "datasets": [
        {"dataset_id": 1, "dataset_group_id": 1, "dataset_name": "customers"},
    ],
    "fields": [
        {
            "field_id": 1,
            "dataset_id": 1,
            "field_name": "email",
            "is_pii": True,
            "datatype_fullname": "varchar",
            "dataset_name": "customers",
        },
    ],
}


# ---------------------------------------------------------------------------
# Template-only rendering (--template, no --format)
# ---------------------------------------------------------------------------


def test_dbt_source_template_renders():
    out, file, files = OutputPipeline().process(
        _FLAT, OutputOptions(template="dbt-source")
    )
    assert out is not None
    assert "customers" in out
    assert "version: 2" in out
    assert file is None
    assert files == []


def test_column_mapping_template_renders():
    out, file, files = OutputPipeline().process(
        _FLAT, OutputOptions(template="column-mapping")
    )
    assert out is not None
    assert "email" in out
    assert "Sales DB" in out


def test_json_template_renders_valid_json():
    out, file, files = OutputPipeline().process(
        _FLAT, OutputOptions(template="json-template")
    )
    assert out is not None
    parsed = json.loads(out)
    assert parsed["resource"] == "datasource"
    assert parsed["datasource"]["datasource_name"] == "Sales DB"
    assert parsed["fields"][0]["field_name"] == "email"
    assert parsed["datasets"][0]["dataset_name"] == "customers"
    assert parsed["datasources"] == []
    assert file is None
    assert files == []


def test_custom_j2_path_renders(tmp_path):
    custom = tmp_path / "custom.j2"
    custom.write_text("datasource: {{ datasource.datasource_name }}", encoding="utf-8")
    out, _, _ = OutputPipeline().process(_FLAT, OutputOptions(template=str(custom)))
    assert out == "datasource: Sales DB"


def test_template_on_list_raises():
    with pytest.raises(ValueError, match="dict"):
        OutputPipeline().process([{"id": 1}], OutputOptions(template="dbt-source"))


# ---------------------------------------------------------------------------
# Template + format conversion
# ---------------------------------------------------------------------------


def test_dbt_source_template_with_format_json_converts():
    out, _, _ = OutputPipeline().process(
        _FLAT, OutputOptions(template="dbt-source", format="json")
    )
    assert out is not None
    parsed = json.loads(out)
    assert isinstance(parsed, (dict, list))


def test_dbt_source_template_with_format_yaml_returns_yaml():
    out, _, _ = OutputPipeline().process(
        _FLAT, OutputOptions(template="dbt-source", format="yaml")
    )
    assert out is not None
    parsed = yaml.safe_load(out)
    assert parsed is not None


def test_dbt_source_template_with_format_yml_alias():
    out, _, _ = OutputPipeline().process(
        _FLAT, OutputOptions(template="dbt-source", format="yml")
    )
    assert out is not None
    yaml.safe_load(out)


def test_json_template_with_format_yaml_converts():
    out, _, _ = OutputPipeline().process(
        _FLAT, OutputOptions(template="json-template", format="yaml")
    )
    assert out is not None
    parsed = yaml.safe_load(out)
    assert isinstance(parsed, dict)
    assert parsed["resource"] == "datasource"


def test_dbt_source_with_json_compact_converts():
    out, _, _ = OutputPipeline().process(
        _FLAT, OutputOptions(template="dbt-source", format="json-compact")
    )
    assert out is not None
    parsed = json.loads(out)
    assert isinstance(parsed, (dict, list))
    assert "\n" not in out


def test_template_with_table_format_raises():
    with pytest.raises(ValueError, match="table"):
        OutputPipeline().process(
            _FLAT, OutputOptions(template="dbt-source", format="table")
        )


def test_unsupported_conversion_raises():
    with pytest.raises(ValueError, match="Cannot convert"):
        OutputPipeline().process(
            _FLAT, OutputOptions(template="dbt-source", format="csv")
        )
