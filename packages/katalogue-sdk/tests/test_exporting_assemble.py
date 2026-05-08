"""Tests for _walk_up_to_system and _slice_from_system_export helpers."""

from unittest.mock import Mock, call


from katalogue.exporting import (
    _slice_from_system_export,
    _walk_up_to_system,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FLAT_SYSTEM = {
    "system": {"system_id": "sys-1", "system_name": "Finance"},
    "datasources": [
        {"datasource_id": "ds-1", "datasource_name": "Warehouse"},
        {"datasource_id": "ds-2", "datasource_name": "Other"},
    ],
    "dataset_groups": [
        {"dataset_group_id": "dg-1", "datasource_id": "ds-1"},
        {"dataset_group_id": "dg-2", "datasource_id": "ds-2"},
    ],
    "datasets": [
        {"dataset_id": "dt-1", "dataset_group_id": "dg-1", "dataset_name": "customers"},
        {"dataset_id": "dt-2", "dataset_group_id": "dg-2", "dataset_name": "orders"},
    ],
    "fields": [
        {"field_id": "f-1", "dataset_id": "dt-1", "dataset_name": "customers"},
        {"field_id": "f-2", "dataset_id": "dt-2", "dataset_name": "orders"},
    ],
}

DS_RECORD = {
    "datasource_id": "ds-1",
    "datasource_name": "Warehouse",
    "system_id": "sys-1",
}
DG_RECORD = {"dataset_group_id": "dg-1", "datasource_id": "ds-1"}
DT_RECORD = {
    "dataset_id": "dt-1",
    "dataset_group_id": "dg-1",
    "dataset_name": "customers",
}


# ---------------------------------------------------------------------------
# _walk_up_to_system
# ---------------------------------------------------------------------------


class TestWalkUpToSystem:
    def _make_client(self, side_effects):
        client = Mock()
        client.get_resource = Mock(side_effect=side_effects)
        return client

    def test_datasource_one_hop(self):
        client = self._make_client([DS_RECORD])
        system_id, ancestors = _walk_up_to_system(client, "datasource", "ds-1")
        assert system_id == "sys-1"
        assert ancestors["datasource"] == DS_RECORD
        client.get_resource.assert_called_once_with("datasource", "ds-1")

    def test_dataset_group_two_hops(self):
        ds_record = {"datasource_id": "ds-1", "system_id": "sys-1"}
        client = self._make_client([DG_RECORD, ds_record])
        system_id, ancestors = _walk_up_to_system(client, "dataset_group", "dg-1")
        assert system_id == "sys-1"
        assert ancestors["dataset_group"] == DG_RECORD
        assert ancestors["datasource"] == ds_record
        assert client.get_resource.call_count == 2

    def test_dataset_three_hops(self):
        ds_record = {"datasource_id": "ds-1", "system_id": "sys-1"}
        client = self._make_client([DT_RECORD, DG_RECORD, ds_record])
        system_id, ancestors = _walk_up_to_system(client, "dataset", "dt-1")
        assert system_id == "sys-1"
        assert ancestors["dataset"] == DT_RECORD
        assert ancestors["dataset_group"] == DG_RECORD
        assert ancestors["datasource"] == ds_record
        assert client.get_resource.call_count == 3

    def test_walk_order_uses_parent_id_fields(self):
        ds_record = {"datasource_id": "ds-1", "system_id": "sys-99"}
        client = self._make_client([DG_RECORD, ds_record])
        system_id, _ = _walk_up_to_system(client, "dataset_group", "dg-1")
        assert system_id == "sys-99"
        assert client.get_resource.call_args_list == [
            call("dataset_group", "dg-1"),
            call("datasource", "ds-1"),
        ]


# ---------------------------------------------------------------------------
# _slice_from_system_export
# ---------------------------------------------------------------------------


class TestSliceFromSystemExport:
    def test_datasource_keeps_only_its_groups(self):
        ancestors = {"datasource": DS_RECORD}
        result = _slice_from_system_export(FLAT_SYSTEM, "datasource", "ds-1", ancestors)
        assert all(g["datasource_id"] == "ds-1" for g in result["dataset_groups"])
        assert len(result["dataset_groups"]) == 1

    def test_datasource_keeps_only_its_datasets(self):
        ancestors = {"datasource": DS_RECORD}
        result = _slice_from_system_export(FLAT_SYSTEM, "datasource", "ds-1", ancestors)
        assert all(d["dataset_group_id"] == "dg-1" for d in result["datasets"])
        assert len(result["datasets"]) == 1

    def test_datasource_keeps_only_its_fields(self):
        ancestors = {"datasource": DS_RECORD}
        result = _slice_from_system_export(FLAT_SYSTEM, "datasource", "ds-1", ancestors)
        assert all(f["dataset_id"] == "dt-1" for f in result["fields"])
        assert len(result["fields"]) == 1

    def test_datasource_singular_dict_is_ancestor_record(self):
        ancestors = {"datasource": DS_RECORD}
        result = _slice_from_system_export(FLAT_SYSTEM, "datasource", "ds-1", ancestors)
        assert result["datasource"] is DS_RECORD

    def test_datasource_preserves_system(self):
        ancestors = {"datasource": DS_RECORD}
        result = _slice_from_system_export(FLAT_SYSTEM, "datasource", "ds-1", ancestors)
        assert result["system"] == FLAT_SYSTEM["system"]

    def test_datasource_metadata(self):
        ancestors = {"datasource": DS_RECORD}
        result = _slice_from_system_export(FLAT_SYSTEM, "datasource", "ds-1", ancestors)
        assert result["resource"] == "datasource"
        assert result["id"] == "ds-1"

    def test_dataset_group_keeps_only_its_datasets(self):
        ancestors = {"dataset_group": DG_RECORD, "datasource": DS_RECORD}
        result = _slice_from_system_export(
            FLAT_SYSTEM, "dataset_group", "dg-1", ancestors
        )
        assert len(result["datasets"]) == 1
        assert result["datasets"][0]["dataset_id"] == "dt-1"

    def test_dataset_group_keeps_only_its_fields(self):
        ancestors = {"dataset_group": DG_RECORD, "datasource": DS_RECORD}
        result = _slice_from_system_export(
            FLAT_SYSTEM, "dataset_group", "dg-1", ancestors
        )
        assert len(result["fields"]) == 1
        assert result["fields"][0]["field_id"] == "f-1"

    def test_dataset_group_singular_dicts(self):
        ancestors = {"dataset_group": DG_RECORD, "datasource": DS_RECORD}
        result = _slice_from_system_export(
            FLAT_SYSTEM, "dataset_group", "dg-1", ancestors
        )
        assert result["dataset_group"] is DG_RECORD
        assert result["datasource"] is DS_RECORD

    def test_dataset_group_metadata(self):
        ancestors = {"dataset_group": DG_RECORD, "datasource": DS_RECORD}
        result = _slice_from_system_export(
            FLAT_SYSTEM, "dataset_group", "dg-1", ancestors
        )
        assert result["resource"] == "dataset_group"
        assert result["id"] == "dg-1"

    def test_dataset_keeps_only_its_fields(self):
        ancestors = {
            "dataset": DT_RECORD,
            "dataset_group": DG_RECORD,
            "datasource": DS_RECORD,
        }
        result = _slice_from_system_export(FLAT_SYSTEM, "dataset", "dt-1", ancestors)
        assert len(result["fields"]) == 1
        assert result["fields"][0]["field_id"] == "f-1"

    def test_dataset_singular_dicts(self):
        ancestors = {
            "dataset": DT_RECORD,
            "dataset_group": DG_RECORD,
            "datasource": DS_RECORD,
        }
        result = _slice_from_system_export(FLAT_SYSTEM, "dataset", "dt-1", ancestors)
        assert result["dataset"] is DT_RECORD
        assert result["dataset_group"] is DG_RECORD
        assert result["datasource"] is DS_RECORD

    def test_dataset_metadata(self):
        ancestors = {
            "dataset": DT_RECORD,
            "dataset_group": DG_RECORD,
            "datasource": DS_RECORD,
        }
        result = _slice_from_system_export(FLAT_SYSTEM, "dataset", "dt-1", ancestors)
        assert result["resource"] == "dataset"
        assert result["id"] == "dt-1"

    def test_datasource_with_no_children_returns_empty_lists(self):
        flat = {**FLAT_SYSTEM, "dataset_groups": [], "datasets": [], "fields": []}
        ancestors = {"datasource": DS_RECORD}
        result = _slice_from_system_export(flat, "datasource", "ds-1", ancestors)
        assert result["dataset_groups"] == []
        assert result["datasets"] == []
        assert result["fields"] == []

    def test_id_is_always_string(self):
        ancestors = {"datasource": DS_RECORD}
        result = _slice_from_system_export(FLAT_SYSTEM, "datasource", 42, ancestors)
        assert result["id"] == "42"
