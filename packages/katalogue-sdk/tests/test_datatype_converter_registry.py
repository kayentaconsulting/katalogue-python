"""Tests for type mapping registry resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from katalogue.datatype_converter import DatatypeConverterConfig
from katalogue.datatype_converter_registry import load_datatype_converter


# ---------------------------------------------------------------------------
# Built-in names
# ---------------------------------------------------------------------------


def test_load_builtin_sqlserver_to_databricks():
    config = load_datatype_converter("sqlserver-to-databricks")
    assert isinstance(config, DatatypeConverterConfig)
    assert "VARCHAR" in config.mappings
    assert config.mappings["VARCHAR"] == "STRING"
    assert "DECIMAL" in config.mappings


def test_load_builtin_db2_to_databricks():
    config = load_datatype_converter("db2-to-databricks")
    assert isinstance(config, DatatypeConverterConfig)
    assert "INTEGER" in config.mappings
    assert config.mappings["INTEGER"] == "INT"


def test_load_builtin_sqlserver_to_pyspark():
    config = load_datatype_converter("sqlserver-to-pyspark")
    assert isinstance(config, DatatypeConverterConfig)
    assert config.mappings["VARCHAR"] == "StringType()"
    assert config.mappings["BIGINT"] == "LongType()"
    assert config.mappings["INT"] == "IntegerType()"
    assert config.mappings["DECIMAL"] == "DecimalType{args}"
    assert config.mappings["DATETIMEOFFSET"] == "TimestampType()"
    assert config.mappings["DATETIME"] == "TimestampNTZType()"


def test_load_builtin_db2_to_pyspark():
    config = load_datatype_converter("db2-to-pyspark")
    assert isinstance(config, DatatypeConverterConfig)
    assert config.mappings["INTEGER"] == "IntegerType()"
    assert config.mappings["BIGINT"] == "LongType()"
    assert config.mappings["DECIMAL"] == "DecimalType{args}"
    assert config.mappings["TIMESTAMP"] == "TimestampNTZType()"


def test_load_builtin_postgres_to_pyspark():
    config = load_datatype_converter("postgres-to-pyspark")
    assert isinstance(config, DatatypeConverterConfig)
    assert config.mappings["VARCHAR"] == "StringType()"
    assert config.mappings["INTEGER"] == "IntegerType()"
    assert config.mappings["BIGINT"] == "LongType()"
    assert config.mappings["NUMERIC"] == "DecimalType{args}"
    assert config.mappings["TIMESTAMPTZ"] == "TimestampType()"
    assert config.mappings["TIMESTAMP"] == "TimestampNTZType()"


def test_load_builtin_postgres_to_databricks():
    config = load_datatype_converter("postgres-to-databricks")
    assert isinstance(config, DatatypeConverterConfig)
    assert config.mappings["VARCHAR"] == "STRING"
    assert config.mappings["INTEGER"] == "INT"
    assert config.mappings["NUMERIC"] == "DECIMAL{args}"
    assert config.mappings["TIMESTAMPTZ"] == "TIMESTAMP_LTZ"
    assert config.mappings["TIMESTAMP"] == "TIMESTAMP_NTZ"
    assert config.mappings["JSON"] == "VARIANT"
    assert config.mappings["JSONB"] == "VARIANT"
    assert config.mappings["XML"] == "VARIANT"


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError, match="Unknown type mapping"):
        load_datatype_converter("oracle-to-snowflake")


# ---------------------------------------------------------------------------
# Direct file path
# ---------------------------------------------------------------------------


def test_load_from_yaml_file(tmp_path):
    mapping_file = tmp_path / "my_mapping.yaml"
    mapping_file.write_text(
        "source: oracle\ntarget: snowflake\nmappings:\n  NUMBER: NUMBER{args}\n  VARCHAR2: VARCHAR\n",
        encoding="utf-8",
    )
    config = load_datatype_converter(str(mapping_file))
    assert config.mappings["NUMBER"] == "NUMBER{args}"
    assert config.mappings["VARCHAR2"] == "VARCHAR"


def test_load_from_yml_extension(tmp_path):
    mapping_file = tmp_path / "my_mapping.yml"
    mapping_file.write_text(
        "mappings:\n  INT: BIGINT\n",
        encoding="utf-8",
    )
    config = load_datatype_converter(str(mapping_file))
    assert config.mappings["INT"] == "BIGINT"


def test_file_not_found_raises(tmp_path):
    with pytest.raises((ValueError, FileNotFoundError)):
        load_datatype_converter(str(tmp_path / "missing.yaml"))


# ---------------------------------------------------------------------------
# Repo-registered name (katalogue.toml)
# ---------------------------------------------------------------------------


def _write_katalogue_toml(repo: Path, name: str, yaml_content: str) -> None:
    mappings_dir = repo / "datatype_converters"
    mappings_dir.mkdir(parents=True, exist_ok=True)
    mapping_file = mappings_dir / f"{name}.yaml"
    mapping_file.write_text(yaml_content, encoding="utf-8")
    (repo / "katalogue.toml").write_text(
        f'[datatype_converters.{name}]\npath = "datatype_converters/{name}.yaml"\n',
        encoding="utf-8",
    )
    (repo / ".git").mkdir(exist_ok=True)


def test_repo_registered_name_resolves(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_katalogue_toml(
        repo,
        "oracle-to-snowflake",
        'mappings:\n  NUMBER: "NUMBER{args}"\n  VARCHAR2: VARCHAR\n',
    )
    monkeypatch.chdir(repo)
    config = load_datatype_converter("oracle-to-snowflake")
    assert config.mappings["NUMBER"] == "NUMBER{args}"


def test_repo_registered_overrides_builtin(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_katalogue_toml(
        repo,
        "sqlserver-to-databricks",
        "mappings:\n  VARCHAR: CUSTOM_STRING\n",
    )
    monkeypatch.chdir(repo)
    config = load_datatype_converter("sqlserver-to-databricks")
    assert config.mappings["VARCHAR"] == "CUSTOM_STRING"
