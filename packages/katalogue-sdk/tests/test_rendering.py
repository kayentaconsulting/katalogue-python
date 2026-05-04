"""Tests for katalogue.rendering — Jinja2 sandbox, built-in templates, filename helpers."""

import importlib.resources

import jinja2
import pytest

from katalogue.rendering import (
    auto_filename,
    get_template_extension,
    is_template_format,
    load_template,
    looks_like_template_path,
    render_filename,
    render_template,
)

# --- format detection ---


def test_json_is_not_template_format():
    assert not is_template_format("json")


def test_compact_is_not_template_format():
    assert not is_template_format("compact")


def test_table_is_not_template_format():
    assert not is_template_format("table")


def test_builtin_name_is_template_format():
    assert is_template_format("dbt-source")


def test_path_is_template_format():
    assert is_template_format("./my.j2")


def test_looks_like_template_path_j2():
    assert looks_like_template_path("./my.j2")


def test_looks_like_template_path_slash():
    assert looks_like_template_path("/path/to/file.j2")


def test_builtin_name_not_a_path():
    assert not looks_like_template_path("dbt-source")


# --- template loading ---


def test_load_builtin_dbt_source():
    tmpl = load_template("dbt-source")
    assert isinstance(tmpl, jinja2.Template)


def test_load_builtin_column_mapping():
    tmpl = load_template("column-mapping")
    assert isinstance(tmpl, jinja2.Template)


def test_load_custom_j2_from_file(tmp_path):
    custom = tmp_path / "custom.j2"
    custom.write_text("hello {{ name }}", encoding="utf-8")
    tmpl = load_template(str(custom))
    assert render_template(tmpl, {"name": "world"}) == "hello world"


def test_load_custom_json_j2_from_file(tmp_path):
    custom = tmp_path / "custom.json.j2"
    custom.write_text("hello {{ name }}", encoding="utf-8")
    tmpl = load_template(str(custom))
    assert render_template(tmpl, {"name": "world"}) == "hello world"


def test_load_j2_json_suffix_is_rejected(tmp_path):
    custom = tmp_path / "custom.j2.json"
    custom.write_text("hello {{ name }}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"\.j2"):
        load_template(str(custom))


def test_load_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_template(str(tmp_path / "missing.j2"))


def test_load_wrong_extension_raises_value_error():
    with pytest.raises(ValueError, match=r"\.j2"):
        load_template("/tmp/file.txt")


def test_load_unknown_name_raises_value_error():
    with pytest.raises(ValueError, match="noext"):
        load_template("noext")


def test_load_unknown_name_lists_builtins():
    with pytest.raises(ValueError, match="dbt-source"):
        load_template("unknown-format")


def test_builtin_template_default_format():
    assert get_template_extension("dbt-source") == "yml"
    assert get_template_extension("json-template") == "json"


# --- sandbox enforcement ---


def test_sandbox_blocks_class_access():
    from jinja2 import StrictUndefined
    from jinja2.sandbox import SandboxedEnvironment

    env = SandboxedEnvironment(undefined=StrictUndefined)
    tmpl = env.from_string('{{ "".__class__ }}')
    with pytest.raises(jinja2.exceptions.SecurityError):
        tmpl.render()


def test_strict_undefined_raises_on_missing_var():
    from katalogue.rendering import _env

    tmpl = _env().from_string("{{ missing_var }}")
    with pytest.raises(jinja2.exceptions.UndefinedError):
        tmpl.render()


# --- rendering built-in templates ---

_DBT_CTX = {
    "dataset_group": {
        "dataset_group_id": 1,
        "dataset_group_name": "public",
        "datasource_id": 1,
    },
    "datasource": {"datasource_id": 1, "datasource_name": "SalesDB"},
    "datasets": [{"dataset_id": 1, "dataset_name": "customers", "dataset_group_id": 1}],
    "fields": [
        {
            "field_id": 1,
            "field_name": "email",
            "dataset_id": 1,
            "is_pii": True,
            "field_is_primary_key": False,
            "datatype_fullname": "varchar",
        },
        {
            "field_id": 2,
            "field_name": "id",
            "dataset_id": 1,
            "is_pii": False,
            "field_is_primary_key": True,
            "datatype_fullname": "int",
        },
    ],
}

_COL_CTX = {
    "datasource": {"datasource_name": "SalesDB"},
    "fields": [
        {
            "field_name": "email",
            "dataset_name": "customers",
            "is_pii": True,
            "datatype_fullname": "varchar",
        },
        {
            "field_name": "id",
            "dataset_name": "customers",
            "is_pii": False,
            "datatype_fullname": "int",
        },
    ],
}


def test_render_dbt_source_contains_table_name():
    output = render_template(load_template("dbt-source"), _DBT_CTX)
    assert "customers" in output
    assert "version: 2" in output


def test_render_column_mapping_contains_field_names():
    output = render_template(load_template("column-mapping"), _COL_CTX)
    assert "email" in output
    assert "id" in output
    assert "SalesDB" in output


# --- filename helpers ---


def test_auto_filename_plain_string():
    assert auto_filename("Customer Orders") == "customer-orders.yml"


def test_auto_filename_strips_slashes():
    result = auto_filename("Customer/Orders")
    assert "/" not in result
    assert result.endswith(".yml")


def test_auto_filename_from_context_with_split_by():
    ctx = {
        "resource": "dataset",
        "dataset": {"dataset_id": 7, "dataset_name": "Foo Bar"},
    }
    assert auto_filename(ctx, split_by="dataset") == "foo-bar.yml"


def test_auto_filename_from_context_no_name_falls_back_to_id():
    ctx = {
        "resource": "dataset",
        "dataset": {"dataset_id": 7},
    }
    result = auto_filename(ctx, split_by="dataset")
    assert "7" in result
    assert result.endswith(".yml")


def test_render_filename_basic():
    result = render_filename(
        "{{ system.system_name }}", {"system": {"system_name": "CRM"}}
    )
    assert result == "CRM"


def test_render_filename_sandbox_blocks_escape():
    with pytest.raises(jinja2.exceptions.SecurityError):
        render_filename("{{ ''.__class__ }}", {})


# --- package data smoke test ---


def test_templates_package_data_accessible():
    pkg = importlib.resources.files("katalogue.templates")
    assert pkg.joinpath("dbt_source.j2").is_file()
    assert pkg.joinpath("column_mapping.j2").is_file()
