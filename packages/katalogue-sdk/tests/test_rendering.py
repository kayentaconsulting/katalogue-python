"""Tests for katalogue.rendering — Jinja2 sandbox, built-in templates, filename helpers."""

import importlib.resources
import json
from pathlib import Path

import jinja2
import pytest


def _fixture(name: str) -> dict:
    p = Path(__file__).parent / "fixtures" / "api_responses" / name
    return json.loads(p.read_text(encoding="utf-8"))

from katalogue.rendering import (
    _build_fields_tree,
    auto_filename,
    dataset_desc,
    field_desc,
    field_is_pii,
    field_is_primary_key,
    field_type,
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


def test_template_dir_macro_import(tmp_path):
    (tmp_path / "my_macros.j2").write_text(
        "{% macro greet(name) %}hello {{ name }}{% endmacro %}", encoding="utf-8"
    )
    (tmp_path / "my_template.j2").write_text(
        "{% from 'my_macros.j2' import greet %}{{ greet('world') }}", encoding="utf-8"
    )
    tmpl = load_template(str(tmp_path / "my_template.j2"))
    assert render_template(tmpl, {}) == "hello world"


def test_project_registered_macro_path(tmp_path):
    macro_dir = tmp_path / "macros"
    macro_dir.mkdir()
    (macro_dir / "helpers.j2").write_text(
        "{% macro shout(name) %}{{ name | upper }}{% endmacro %}", encoding="utf-8"
    )
    (tmp_path / "katalogue.toml").write_text(
        '[macro_paths]\npaths = ["macros/"]\n', encoding="utf-8"
    )
    (tmp_path / "my_template.j2").write_text(
        "{% from 'helpers.j2' import shout %}{{ shout('hello') }}", encoding="utf-8"
    )
    tmpl = load_template(str(tmp_path / "my_template.j2"))
    assert render_template(tmpl, {}) == "HELLO"


def test_loader_enables_from_import(tmp_path):
    from katalogue.rendering import _env

    (tmp_path / "shared.j2").write_text(
        "{% macro echo(name) %}hi {{ name }}{% endmacro %}", encoding="utf-8"
    )
    tmpl = _env([tmp_path]).from_string(
        "{% from 'shared.j2' import echo %}{{ echo('there') }}"
    )
    assert tmpl.render() == "hi there"


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


# --- nested-yml template ---

_NESTED_CTX = _fixture("dataset.json")


def test_load_builtin_nested_fields():
    tmpl = load_template("nested-yml")
    assert isinstance(tmpl, jinja2.Template)


def test_nested_fields_default_format():
    assert get_template_extension("nested-yml") == "yml"


def test_render_nested_fields_contains_dataset_name():
    output = render_template(load_template("nested-yml"), _NESTED_CTX)
    assert "TEST_TABLE" in output


def test_render_nested_fields_struct_parent_has_fields_key():
    output = render_template(load_template("nested-yml"), _NESTED_CTX)
    assert "METADATA" in output
    assert "fields:" in output


def test_render_nested_fields_child_follows_parent():
    output = render_template(load_template("nested-yml"), _NESTED_CTX)
    metadata_pos = output.index("METADATA")
    source_pos = output.index("name: source")
    assert source_pos > metadata_pos


def test_render_nested_fields_flat_field_at_root():
    output = render_template(load_template("nested-yml"), _NESTED_CTX)
    assert "ID" in output


# --- domain helpers ---


def test_field_type_prefers_datatype_converted():
    f = {
        "datatype_converted": "STRING",
        "datatype_fullname": "varchar(255)",
        "field_datatype": "VARCHAR",
    }
    assert field_type(f) == "STRING"


def test_field_type_falls_back_to_fullname():
    f = {"datatype_fullname": "varchar(255)", "field_datatype": "VARCHAR"}
    assert field_type(f) == "varchar(255)"


def test_field_type_falls_back_to_field_datatype():
    assert field_type({"field_datatype": "VARCHAR"}) == "VARCHAR"


def test_field_type_empty_when_all_missing():
    assert field_type({}) == ""


def test_field_desc_prefers_source_description():
    f = {"field_source_description": "src", "description": "doc"}
    assert field_desc(f) == "src"


def test_field_desc_falls_back_to_description():
    assert field_desc({"description": "doc"}) == "doc"


def test_field_desc_empty_when_missing():
    assert field_desc({}) == ""


def test_field_is_pii_true_when_is_pii():
    assert field_is_pii({"is_pii": True}) is True


def test_field_is_pii_true_when_field_is_pii():
    assert field_is_pii({"field_is_pii": True}) is True


def test_field_is_pii_false_when_neither():
    assert field_is_pii({}) is False
    assert field_is_pii({"is_pii": False, "field_is_pii": False}) is False


def test_field_is_primary_key_reads_flag():
    assert field_is_primary_key({"field_is_primary_key": True}) is True
    assert field_is_primary_key({}) is False


def test_dataset_desc_fallback():
    assert dataset_desc({"dataset_description": "a", "description": "b"}) == "a"
    assert dataset_desc({"description": "b"}) == "b"
    assert dataset_desc({}) == ""


# --- fields_tree ---


def _tree_fixture() -> list[dict]:
    return [
        {
            "field_id": "f-1",
            "field_name": "address",
            "dataset_id": 1,
            "parent_field_id": None,
        },
        {
            "field_id": "f-2",
            "field_name": "street",
            "dataset_id": 1,
            "parent_field_id": "f-1",
        },
        {
            "field_id": "f-3",
            "field_name": "number",
            "dataset_id": 1,
            "parent_field_id": "f-2",
        },
        {
            "field_id": "f-4",
            "field_name": "id",
            "dataset_id": 1,
            "parent_field_id": None,
        },
        {
            "field_id": "f-5",
            "field_name": "other_root",
            "dataset_id": 2,
            "parent_field_id": None,
        },
    ]


def test_fields_tree_groups_children_under_parents():
    tree = _build_fields_tree(_tree_fixture(), dataset_id=1)
    assert [r["field_name"] for r in tree] == ["address", "id"]
    address = tree[0]
    assert [c["field_name"] for c in address["children"]] == ["street"]
    street = address["children"][0]
    assert [c["field_name"] for c in street["children"]] == ["number"]
    assert street["children"][0]["children"] == []


def test_fields_tree_filters_by_dataset_id():
    tree = _build_fields_tree(_tree_fixture(), dataset_id=1)
    field_names = {r["field_name"] for r in tree}
    assert "other_root" not in field_names


def test_fields_tree_no_arg_returns_all_roots():
    tree = _build_fields_tree(_tree_fixture())
    field_names = {r["field_name"] for r in tree}
    assert {"address", "id", "other_root"} <= field_names


def test_fields_tree_promotes_orphan_to_root():
    fields = [
        {
            "field_id": "f-2",
            "field_name": "child",
            "dataset_id": 1,
            "parent_field_id": "missing",
        },
    ]
    tree = _build_fields_tree(fields, dataset_id=1)
    assert [r["field_name"] for r in tree] == ["child"]


def test_fields_tree_attaches_dotted_field_path():
    tree = _build_fields_tree(_tree_fixture(), dataset_id=1)
    address = next(r for r in tree if r["field_name"] == "address")
    assert address["field_path"] == "address"
    street = address["children"][0]
    assert street["field_path"] == "address.street"
    number = street["children"][0]
    assert number["field_path"] == "address.street.number"


def test_fields_tree_returns_copies_not_references():
    fields = _tree_fixture()
    tree = _build_fields_tree(fields, dataset_id=1)
    tree[0]["mutated"] = True
    assert "mutated" not in fields[0]


def test_fields_tree_isolated_between_renders():
    from jinja2 import StrictUndefined
    from jinja2.sandbox import SandboxedEnvironment

    env = SandboxedEnvironment(undefined=StrictUndefined)
    tmpl = env.from_string(
        "{% for f in fields_tree() %}{{ f.field_name }} {% endfor %}"
    )
    out_a = render_template(
        tmpl, {"fields": [{"field_id": 1, "field_name": "a", "parent_field_id": None}]}
    )
    out_b = render_template(
        tmpl, {"fields": [{"field_id": 1, "field_name": "b", "parent_field_id": None}]}
    )
    assert out_a.strip() == "a"
    assert out_b.strip() == "b"


# --- expected-render equivalence for built-in templates ---


_GOLDEN_CTX = _fixture("dataset_group.json")


def _expected_render(name: str) -> str:
    return (Path(__file__).parent / "fixtures" / "expected_renders" / name).read_text(
        encoding="utf-8"
    )


def test_dbt_source_byte_identical_to_expected_render():
    rendered = render_template(load_template("dbt-source"), _GOLDEN_CTX)
    assert rendered == _expected_render("dbt_source_expected.yml")


def test_nested_yml_byte_identical_to_expected_render():
    rendered = render_template(load_template("nested-yml"), _GOLDEN_CTX)
    assert rendered == _expected_render("nested_yml_expected.yml")


# --- helpers available in templates ---


def test_helpers_registered_as_jinja_globals():
    from katalogue.rendering import _env

    tmpl = _env().from_string(
        "{{ field_type(f) }}|{{ field_desc(f) }}|{{ field_is_pii(f) }}"
    )
    out = tmpl.render(
        f={"datatype_converted": "INT", "description": "n", "is_pii": True}
    )
    assert out == "INT|n|True"
