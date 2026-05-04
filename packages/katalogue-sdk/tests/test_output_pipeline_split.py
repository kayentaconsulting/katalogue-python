"""Tests for OutputPipeline — split-by path."""

import pytest

from katalogue.options import OutputOptions
from katalogue.output import OutputPipeline

_FLAT_SYSTEM = {
    "resource": "system",
    "id": "1",
    "system": {"system_id": 1, "system_name": "Finance"},
    "datasources": [{"datasource_id": 1, "datasource_name": "Sales DB"}],
    "dataset_groups": [
        {"dataset_group_id": 1, "datasource_id": 1, "dataset_group_name": "public"},
        {"dataset_group_id": 2, "datasource_id": 1, "dataset_group_name": "private"},
    ],
    "datasets": [
        {"dataset_id": 1, "dataset_group_id": 1, "dataset_name": "customers"},
        {"dataset_id": 2, "dataset_group_id": 2, "dataset_name": "orders"},
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
        {
            "field_id": 2,
            "dataset_id": 2,
            "field_name": "amount",
            "is_pii": False,
            "datatype_fullname": "numeric",
            "dataset_name": "orders",
        },
    ],
}

_FLAT_DATASET = {
    "resource": "dataset",
    "id": "1",
    "system": {"system_id": 1, "system_name": "Finance"},
    "datasource": {"datasource_id": 1, "datasource_name": "Sales DB"},
    "dataset_group": {
        "dataset_group_id": 1,
        "datasource_id": 1,
        "dataset_group_name": "public",
    },
    "dataset": {"dataset_id": 1, "dataset_group_id": 1, "dataset_name": "customers"},
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


def test_split_by_dataset_creates_two_files(tmp_path):
    _, _, files = OutputPipeline().process(
        _FLAT_SYSTEM,
        OutputOptions(
            template="dbt-source", split_by="dataset", output_dir=str(tmp_path)
        ),
        root_resource="system",
    )
    assert len(files) == 2
    paths = {f.path for f in files}
    on_disk = {str(p) for p in tmp_path.iterdir()}
    assert paths == on_disk


def test_split_by_dataset_written_file_fields(tmp_path):
    _, _, files = OutputPipeline().process(
        _FLAT_SYSTEM,
        OutputOptions(
            template="dbt-source", split_by="dataset", output_dir=str(tmp_path)
        ),
        root_resource="system",
    )
    keys = {f.split_key for f in files}
    assert keys == {"dataset"}
    values = {f.split_value for f in files}
    assert "customers" in values
    assert "orders" in values


def test_split_output_is_none(tmp_path):
    output, _, _ = OutputPipeline().process(
        _FLAT_SYSTEM,
        OutputOptions(
            template="dbt-source", split_by="dataset", output_dir=str(tmp_path)
        ),
        root_resource="system",
    )
    assert output is None


def test_split_dry_run_no_files_on_disk(tmp_path):
    _, _, files = OutputPipeline().process(
        _FLAT_SYSTEM,
        OutputOptions(
            template="dbt-source",
            split_by="dataset",
            output_dir=str(tmp_path),
            dry_run=True,
        ),
        root_resource="system",
    )
    assert len(files) == 2
    assert list(tmp_path.iterdir()) == []


def test_split_by_datasource(tmp_path):
    _, _, files = OutputPipeline().process(
        _FLAT_SYSTEM,
        OutputOptions(
            template="column-mapping", split_by="datasource", output_dir=str(tmp_path)
        ),
        root_resource="system",
    )
    assert len(files) == 1
    assert files[0].split_key == "datasource"
    assert files[0].split_value == "Sales DB"


def test_split_single_dataset_root(tmp_path):
    _, _, files = OutputPipeline().process(
        _FLAT_DATASET,
        OutputOptions(
            template="dbt-source", split_by="dataset", output_dir=str(tmp_path)
        ),
        root_resource="dataset",
    )
    assert len(files) == 1


def test_split_invalid_split_by_raises():
    with pytest.raises(ValueError, match="glossary"):
        OutputPipeline().process(
            {"resource": "glossary", "id": "1", "glossary": {}, "terms": []},
            OutputOptions(
                template="column-mapping", split_by="dataset", output_dir="/tmp"
            ),
            root_resource="glossary",
        )


def test_split_filename_template(tmp_path):
    _, _, files = OutputPipeline().process(
        _FLAT_SYSTEM,
        OutputOptions(
            template="dbt-source",
            split_by="dataset",
            output_dir=str(tmp_path),
            filename_template="{{ dataset.dataset_id }}.yml",
        ),
        root_resource="system",
    )
    filenames = {f.path.split("\\")[-1].split("/")[-1] for f in files}
    assert "1.yml" in filenames
    assert "2.yml" in filenames


def test_split_duplicate_names_deduped(tmp_path):
    data = {
        "resource": "system",
        "id": "1",
        "system": {"system_id": 1, "system_name": "Fin"},
        "datasources": [{"datasource_id": 1, "datasource_name": "DB"}],
        "dataset_groups": [
            {"dataset_group_id": 1, "datasource_id": 1, "dataset_group_name": "pub"},
            {"dataset_group_id": 2, "datasource_id": 1, "dataset_group_name": "pub"},
        ],
        "datasets": [
            {"dataset_id": 1, "dataset_group_id": 1, "dataset_name": "same"},
            {"dataset_id": 2, "dataset_group_id": 2, "dataset_name": "same"},
        ],
        "fields": [],
    }
    _, _, files = OutputPipeline().process(
        data,
        OutputOptions(
            template="dbt-source", split_by="dataset", output_dir=str(tmp_path)
        ),
        root_resource="system",
    )
    assert len(files) == 2
    paths = [f.path for f in files]
    assert len(set(paths)) == 2
