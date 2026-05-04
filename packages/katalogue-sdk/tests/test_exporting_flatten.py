"""Tests for flatten_system_export — normalises the nested export API response."""

from katalogue.exporting import flatten_system_export

NESTED_EXPORT = {
    "data": {
        "system": {
            "system_id": "sys-1",
            "system_name": "Finance",
            "datasources": [
                {
                    "datasource_id": "ds-1",
                    "datasource_name": "Warehouse",
                    "dataset_groups": [
                        {
                            "dataset_group_id": "dg-1",
                            "dataset_group_name": "public",
                            "datasets": [
                                {
                                    "dataset_id": "dt-1",
                                    "dataset_name": "customers",
                                    "fields": [
                                        {
                                            "field_id": "f-1",
                                            "field_name": "email",
                                            "field_is_pii": True,
                                            "field_datatype": "varchar",
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    }
}


def test_flatten_hoists_datasources():
    result = flatten_system_export(NESTED_EXPORT)
    assert len(result["datasources"]) == 1
    assert result["datasources"][0]["datasource_id"] == "ds-1"


def test_flatten_hoists_dataset_groups_with_parent_id():
    result = flatten_system_export(NESTED_EXPORT)
    assert len(result["dataset_groups"]) == 1
    group = result["dataset_groups"][0]
    assert group["dataset_group_id"] == "dg-1"
    assert group["datasource_id"] == "ds-1"


def test_flatten_hoists_datasets_with_parent_id():
    result = flatten_system_export(NESTED_EXPORT)
    assert len(result["datasets"]) == 1
    ds = result["datasets"][0]
    assert ds["dataset_id"] == "dt-1"
    assert ds["dataset_group_id"] == "dg-1"


def test_flatten_hoists_fields_with_parent_id_and_dataset_name():
    result = flatten_system_export(NESTED_EXPORT)
    assert len(result["fields"]) == 1
    f = result["fields"][0]
    assert f["field_id"] == "f-1"
    assert f["dataset_id"] == "dt-1"
    assert f["dataset_name"] == "customers"


def test_flatten_field_is_pii_compat_alias():
    result = flatten_system_export(NESTED_EXPORT)
    f = result["fields"][0]
    assert f["is_pii"] is True


def test_flatten_field_datatype_compat_alias():
    result = flatten_system_export(NESTED_EXPORT)
    f = result["fields"][0]
    assert f["datatype_fullname"] == "varchar"


def test_flatten_system_dict_excludes_datasources_key():
    result = flatten_system_export(NESTED_EXPORT)
    assert "datasources" not in result["system"]


def test_flatten_datasource_excludes_dataset_groups_key():
    result = flatten_system_export(NESTED_EXPORT)
    ds = result["datasources"][0]
    assert "dataset_groups" not in ds


def test_flatten_dataset_excludes_fields_key():
    result = flatten_system_export(NESTED_EXPORT)
    dataset = result["datasets"][0]
    assert "fields" not in dataset


def test_flatten_empty_system():
    response = {"data": {"system": {"system_id": "sys-1", "system_name": "Empty"}}}
    result = flatten_system_export(response)
    assert result["system"]["system_id"] == "sys-1"
    assert result["datasources"] == []
    assert result["dataset_groups"] == []
    assert result["datasets"] == []
    assert result["fields"] == []


def test_flatten_multiple_datasources_and_groups():
    response = {
        "data": {
            "system": {
                "system_id": "sys-1",
                "datasources": [
                    {
                        "datasource_id": "ds-1",
                        "dataset_groups": [
                            {"dataset_group_id": "dg-1", "datasets": []},
                            {"dataset_group_id": "dg-2", "datasets": []},
                        ],
                    },
                    {
                        "datasource_id": "ds-2",
                        "dataset_groups": [],
                    },
                ],
            }
        }
    }
    result = flatten_system_export(response)
    assert len(result["datasources"]) == 2
    assert len(result["dataset_groups"]) == 2
    assert all(g["datasource_id"] == "ds-1" for g in result["dataset_groups"])
