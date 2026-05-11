"""Tests for type mapping — apply_datatype_converter and enrich_fields_with_converted_datatype."""

from __future__ import annotations

import pytest

from katalogue.datatype_converter import (
    DatatypeConverterConfig,
    apply_datatype_converter,
    enrich_fields_with_converted_datatype,
)

_MAPPINGS: dict[str, str] = {
    "VARCHAR": "STRING",
    "NVARCHAR": "STRING",
    "DECIMAL": "DECIMAL{args}",
    "NUMERIC": "DECIMAL{args}",
    "INT": "INT",
    "FLOAT": "DOUBLE",
}

_CONFIG = DatatypeConverterConfig(
    source="sqlserver", target="databricks", mappings=_MAPPINGS
)


# ---------------------------------------------------------------------------
# apply_datatype_converter — pure function
# ---------------------------------------------------------------------------


def test_exact_match_strips_precision():
    assert apply_datatype_converter("VARCHAR(255)", _MAPPINGS) == "STRING"


def test_args_placeholder_preserves_precision():
    assert apply_datatype_converter("DECIMAL(10,2)", _MAPPINGS) == "DECIMAL(10,2)"


def test_args_placeholder_rename_preserves_args():
    assert apply_datatype_converter("NUMERIC(18,4)", _MAPPINGS) == "DECIMAL(18,4)"


def test_case_insensitive_lookup():
    assert apply_datatype_converter("varchar(255)", _MAPPINGS) == "STRING"
    assert apply_datatype_converter("Decimal(10,2)", _MAPPINGS) == "DECIMAL(10,2)"


def test_unknown_type_passthrough():
    assert apply_datatype_converter("BLOB", _MAPPINGS) == "BLOB"
    assert apply_datatype_converter("BLOB(1024)", _MAPPINGS) == "BLOB(1024)"


def test_bare_type_no_args():
    assert apply_datatype_converter("INT", _MAPPINGS) == "INT"
    assert apply_datatype_converter("FLOAT", _MAPPINGS) == "DOUBLE"


def test_empty_mappings_passthrough():
    assert apply_datatype_converter("VARCHAR(255)", {}) == "VARCHAR(255)"


def test_args_placeholder_on_bare_input():
    # DECIMAL mapped with {args}, but input has no args — result has no parens
    assert apply_datatype_converter("DECIMAL", _MAPPINGS) == "DECIMAL"


# ---------------------------------------------------------------------------
# enrich_fields_with_converted_datatype
# ---------------------------------------------------------------------------


def test_enrich_adds_datatype_converted():
    fields = [{"field_name": "price", "datatype_fullname": "DECIMAL(10,2)"}]
    enrich_fields_with_converted_datatype(fields, _CONFIG)
    assert fields[0]["datatype_converted"] == "DECIMAL(10,2)"


def test_enrich_strips_precision_when_no_args_placeholder():
    fields = [{"field_name": "name", "datatype_fullname": "VARCHAR(100)"}]
    enrich_fields_with_converted_datatype(fields, _CONFIG)
    assert fields[0]["datatype_converted"] == "STRING"


def test_enrich_field_without_datatype_is_skipped():
    fields = [{"field_name": "x"}]
    enrich_fields_with_converted_datatype(fields, _CONFIG)
    assert "datatype_converted" not in fields[0]


def test_enrich_noop_when_config_is_none():
    fields = [{"field_name": "x", "datatype_fullname": "VARCHAR(100)"}]
    enrich_fields_with_converted_datatype(fields, None)
    assert "datatype_converted" not in fields[0]


def test_enrich_multiple_fields():
    fields = [
        {"field_name": "a", "datatype_fullname": "INT"},
        {"field_name": "b", "datatype_fullname": "FLOAT"},
        {"field_name": "c", "datatype_fullname": "UNKNOWN_TYPE"},
    ]
    enrich_fields_with_converted_datatype(fields, _CONFIG)
    assert fields[0]["datatype_converted"] == "INT"
    assert fields[1]["datatype_converted"] == "DOUBLE"
    assert fields[2]["datatype_converted"] == "UNKNOWN_TYPE"


# ---------------------------------------------------------------------------
# DatatypeConverterConfig validation
# ---------------------------------------------------------------------------


def test_config_rejects_extra_fields():
    with pytest.raises(Exception):
        DatatypeConverterConfig(source="a", target="b", mappings={}, unexpected="x")  # type: ignore[call-arg]
