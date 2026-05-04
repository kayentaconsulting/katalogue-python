"""Tests for apply_filter (all operators) and apply_hierarchical_filters (level pruning)."""

from katalogue.exporting import apply_hierarchical_filters
from katalogue.filters import Filter, apply_filter

# --- apply_filter — single-row matching ---

_ROW = {
    "name": "CRM",
    "count": 5,
    "is_pii": False,
    "field_is_pii": True,
    "custom_attributes": [{"code": "A"}, {"code": "B"}],
}


def _f(path: str, op: str, value: object) -> Filter:
    return Filter(path=path, operator=op, value=value)  # type: ignore[arg-type]


# --- equality ---


def test_apply_filter_eq_match() -> None:
    assert apply_filter({"name": "CRM"}, _f("name", "=", "CRM"))


def test_apply_filter_eq_no_match() -> None:
    assert not apply_filter({"name": "ERP"}, _f("name", "=", "CRM"))


def test_apply_filter_eq_case_insensitive() -> None:
    assert apply_filter({"name": "crm"}, _f("name", "=", "CRM"))


def test_apply_filter_neq_match() -> None:
    assert apply_filter({"name": "ERP"}, _f("name", "!=", "CRM"))


def test_apply_filter_neq_no_match() -> None:
    assert not apply_filter({"name": "CRM"}, _f("name", "!=", "CRM"))


# --- comparison ---


def test_apply_filter_gt() -> None:
    assert apply_filter({"count": 6}, _f("count", ">", 5))
    assert not apply_filter({"count": 5}, _f("count", ">", 5))


def test_apply_filter_gte() -> None:
    assert apply_filter({"count": 5}, _f("count", ">=", 5))
    assert not apply_filter({"count": 4}, _f("count", ">=", 5))


def test_apply_filter_lt() -> None:
    assert apply_filter({"count": 4}, _f("count", "<", 5))
    assert not apply_filter({"count": 5}, _f("count", "<", 5))


def test_apply_filter_lte() -> None:
    assert apply_filter({"count": 5}, _f("count", "<=", 5))
    assert not apply_filter({"count": 6}, _f("count", "<=", 5))


def test_apply_filter_comparison_missing_key_no_match() -> None:
    assert not apply_filter({}, _f("count", ">", 5))


# --- in / not-in ---


def test_apply_filter_in_match() -> None:
    assert apply_filter({"t": "db"}, _f("t", "in", ["db", "api"]))


def test_apply_filter_in_no_match() -> None:
    assert not apply_filter({"t": "csv"}, _f("t", "in", ["db", "api"]))


def test_apply_filter_in_case_insensitive() -> None:
    assert apply_filter({"t": "DB"}, _f("t", "in", ["db", "api"]))


def test_apply_filter_not_in_match() -> None:
    assert apply_filter({"t": "csv"}, _f("t", "not-in", ["db", "api"]))


def test_apply_filter_not_in_no_match() -> None:
    assert not apply_filter({"t": "db"}, _f("t", "not-in", ["db", "api"]))


# --- contains ---


def test_apply_filter_contains_match() -> None:
    assert apply_filter({"desc": "contains PII data"}, _f("desc", "contains", "pii"))


def test_apply_filter_contains_no_match() -> None:
    assert not apply_filter({"desc": "safe data"}, _f("desc", "contains", "pii"))


def test_apply_filter_contains_missing_key_no_match() -> None:
    assert not apply_filter({}, _f("desc", "contains", "pii"))


# --- startswith / endswith ---


def test_apply_filter_startswith_match() -> None:
    assert apply_filter({"name": "CRM Platform"}, _f("name", "startswith", "crm"))


def test_apply_filter_startswith_no_match() -> None:
    assert not apply_filter({"name": "Platform CRM"}, _f("name", "startswith", "crm"))


def test_apply_filter_endswith_match() -> None:
    assert apply_filter({"name": "CRM Platform"}, _f("name", "endswith", "platform"))


def test_apply_filter_endswith_no_match() -> None:
    assert not apply_filter(
        {"name": "Platform CRM"}, _f("name", "endswith", "platform")
    )


# --- field_* prefix fallback ---


def test_apply_filter_field_prefix_fallback() -> None:
    assert apply_filter({"field_is_pii": True}, _f("is_pii", "=", True))


# --- dotted path — nested list lookup ---


def test_apply_filter_dotted_path_eq_any_match() -> None:
    row = {"attrs": [{"code": "A"}, {"code": "B"}]}
    assert apply_filter(row, _f("attrs.code", "=", "a"))


def test_apply_filter_dotted_path_neq_all_must_mismatch() -> None:
    row = {"attrs": [{"code": "A"}, {"code": "B"}]}
    assert not apply_filter(row, _f("attrs.code", "!=", "a"))


def test_apply_filter_dotted_path_absent_list_neq_true() -> None:
    assert apply_filter({}, _f("attrs.code", "!=", "x"))


def test_apply_filter_dotted_path_startswith_any_match() -> None:
    row = {"attrs": [{"code": "CRM"}, {"code": "ERP"}]}
    assert apply_filter(row, _f("attrs.code", "startswith", "cr"))


def test_apply_filter_dotted_path_endswith_any_match() -> None:
    row = {"attrs": [{"code": "CRM"}, {"code": "ERP"}]}
    assert apply_filter(row, _f("attrs.code", "endswith", "rp"))


# --- apply_hierarchical_filters ---


def _flat_ds() -> dict:
    return {
        "resource": "datasource",
        "id": "ds-1",
        "system": {"system_id": "sys-1", "system_name": "Finance"},
        "datasource": {"datasource_id": "ds-1", "datasource_name": "Sales DB"},
        "dataset_groups": [
            {
                "dataset_group_id": "dg-1",
                "datasource_id": "ds-1",
                "dataset_group_name": "public",
            },
            {
                "dataset_group_id": "dg-2",
                "datasource_id": "ds-1",
                "dataset_group_name": "private",
            },
        ],
        "datasets": [
            {
                "dataset_id": "dt-1",
                "dataset_group_id": "dg-1",
                "dataset_name": "customers",
            },
            {
                "dataset_id": "dt-2",
                "dataset_group_id": "dg-2",
                "dataset_name": "orders",
            },
        ],
        "fields": [
            {
                "field_id": "f-1",
                "dataset_id": "dt-1",
                "field_name": "email",
                "is_pii": True,
            },
            {
                "field_id": "f-2",
                "dataset_id": "dt-1",
                "field_name": "id",
                "is_pii": False,
            },
            {
                "field_id": "f-3",
                "dataset_id": "dt-2",
                "field_name": "amount",
                "is_pii": False,
            },
        ],
    }


def test_hierarchical_filter_pii_fields_prunes_parents() -> None:
    result = apply_hierarchical_filters(
        _flat_ds(),
        [_f("field.is_pii", "=", True)],
        root_resource="datasource",
    )
    assert [f["field_id"] for f in result["fields"]] == ["f-1"]
    assert [d["dataset_id"] for d in result["datasets"]] == ["dt-1"]
    assert [g["dataset_group_id"] for g in result["dataset_groups"]] == ["dg-1"]


def test_hierarchical_filter_dataset_name_neq() -> None:
    result = apply_hierarchical_filters(
        _flat_ds(),
        [_f("dataset.dataset_name", "!=", "customers")],
        root_resource="datasource",
    )
    assert [d["dataset_id"] for d in result["datasets"]] == ["dt-2"]


def test_hierarchical_filter_system_level_no_match_empties_all() -> None:
    result = apply_hierarchical_filters(
        _flat_ds(),
        [_f("system.system_name", "!=", "Finance")],
        root_resource="datasource",
    )
    assert result["datasource"] is None
    assert result["dataset_groups"] == []
    assert result["datasets"] == []
    assert result["fields"] == []


def test_hierarchical_filter_no_filters_returns_unchanged() -> None:
    data = _flat_ds()
    result = apply_hierarchical_filters(data, [], root_resource="datasource")
    assert result == data


def test_hierarchical_filter_bare_key_scoped_to_root() -> None:
    result = apply_hierarchical_filters(
        _flat_ds(),
        [_f("datasource_name", "=", "Sales DB")],
        root_resource="datasource",
    )
    assert result["datasource"]["datasource_id"] == "ds-1"


def test_hierarchical_filter_bare_key_root_no_match_empties() -> None:
    result = apply_hierarchical_filters(
        _flat_ds(),
        [_f("datasource_name", "=", "Other")],
        root_resource="datasource",
    )
    assert result["datasource"] is None


def test_hierarchical_filter_multiple_and_logic() -> None:
    result = apply_hierarchical_filters(
        _flat_ds(),
        [_f("field.is_pii", "=", False), _f("dataset.name", "=", "orders")],
        root_resource="datasource",
    )
    field_ids = [f["field_id"] for f in result["fields"]]
    assert "f-3" in field_ids
    assert "f-1" not in field_ids


def test_hierarchical_filter_gte_on_list() -> None:
    data = _flat_ds()
    result = apply_hierarchical_filters(
        data,
        [_f("field.field_id", "in", ["f-1", "f-3"])],
        root_resource="datasource",
    )
    field_ids = {f["field_id"] for f in result["fields"]}
    assert field_ids == {"f-1", "f-3"}
