"""Tests for _walk_up_to_system and _slice_from_system_export helpers."""

from unittest.mock import Mock, call


from katalogue.exporting import (
    _build_glossary_tree,
    _slice_from_system_export,
    _walk_up_to_system,
    assemble_glossary,
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


# ---------------------------------------------------------------------------
# _build_glossary_tree — flat assets -> recursive business-term hierarchy
# ---------------------------------------------------------------------------

# Mirrors the real glossary export: business terms encode their own identity in
# full_path (empty for top-level); field descriptions carry their PARENT term's
# full_path. The same field description id may attach to multiple terms.
_ASSETS = [
    {"id": 15, "name": "Customer", "asset_type": "business_term", "full_path": ""},
    {
        "id": 210,
        "name": "Customer ID",
        "asset_type": "field_description",
        "full_path": "Customer",
    },
    {
        "id": 19,
        "name": "Sales Order",
        "asset_type": "business_term",
        "full_path": "Customer::Sales Order",
    },
    {
        "id": 209,
        "name": "Sales Order ID",
        "asset_type": "field_description",
        "full_path": "Customer::Sales Order",
    },
    {
        "id": 22,
        "name": "Discount",
        "asset_type": "business_term",
        "full_path": "Customer::Sales Order::Discount",
    },
    {"id": 14, "name": "Product", "asset_type": "business_term", "full_path": ""},
    {
        "id": 17,
        "name": "List Price",
        "asset_type": "business_term",
        "full_path": "Customer::Sales Order::List Price",
    },
    # Field description 205 attaches to BOTH the "List Price" term and "Product".
    {
        "id": 205,
        "name": "List Price",
        "asset_type": "field_description",
        "full_path": "Customer::Sales Order::List Price",
    },
    {
        "id": 205,
        "name": "List Price",
        "asset_type": "field_description",
        "full_path": "Product",
    },
]


def _node_by_id(nodes, node_id):
    return next(n for n in nodes if n["id"] == node_id)


class TestBuildGlossaryTree:
    def test_nests_business_terms_three_levels(self):
        roots, orphans = _build_glossary_tree(_ASSETS)
        assert orphans == []
        customer = _node_by_id(roots, 15)
        sales_order = _node_by_id(customer["business_terms"], 19)
        discount = _node_by_id(sales_order["business_terms"], 22)
        assert discount["name"] == "Discount"

    def test_attaches_field_descriptions_to_parent_term(self):
        roots, _ = _build_glossary_tree(_ASSETS)
        customer = _node_by_id(roots, 15)
        assert [fd["id"] for fd in customer["field_descriptions"]] == [210]
        sales_order = _node_by_id(customer["business_terms"], 19)
        assert [fd["id"] for fd in sales_order["field_descriptions"]] == [209]

    def test_many_to_many_fd_appears_under_each_parent(self):
        roots, _ = _build_glossary_tree(_ASSETS)
        product = _node_by_id(roots, 14)
        assert [fd["id"] for fd in product["field_descriptions"]] == [205]
        customer = _node_by_id(roots, 15)
        sales_order = _node_by_id(customer["business_terms"], 19)
        list_price = _node_by_id(sales_order["business_terms"], 17)
        assert [fd["id"] for fd in list_price["field_descriptions"]] == [205]

    def test_every_node_has_both_child_keys(self):
        roots, _ = _build_glossary_tree(_ASSETS)
        product = _node_by_id(roots, 14)
        assert product["business_terms"] == []
        assert isinstance(product["field_descriptions"], list)

    def test_promotes_orphan_term_to_root(self):
        assets = [
            {
                "id": 99,
                "name": "Ghost",
                "asset_type": "business_term",
                "full_path": "Nowhere::Ghost",
            }
        ]
        roots, orphans = _build_glossary_tree(assets)
        assert _node_by_id(roots, 99)["name"] == "Ghost"
        assert orphans == []

    def test_promotes_orphan_field_description_to_root(self):
        assets = [
            {
                "id": 500,
                "name": "Lonely",
                "asset_type": "field_description",
                "full_path": "DoesNotExist",
            }
        ]
        roots, orphans = _build_glossary_tree(assets)
        assert roots == []
        assert [fd["id"] for fd in orphans] == [500]

    def test_empty_assets(self):
        assert _build_glossary_tree([]) == ([], [])


class TestAssembleGlossary:
    def _client(self):
        client = Mock()
        client.get_glossary_export = Mock(
            return_value={
                "export": {
                    "meta": {"katalogue_version": "0.23.0"},
                    "data": {
                        "glossary_id": 2,
                        "glossary_name": "Common Information Model",
                        "assets": _ASSETS,
                    },
                }
            }
        )
        return client

    def test_returns_business_terms_tree_not_flat_terms(self):
        result = assemble_glossary(self._client(), 2)
        assert "terms" not in result
        root_ids = {n["id"] for n in result["business_terms"]}
        assert {14, 15} <= root_ids

    def test_returns_glossary_metadata(self):
        result = assemble_glossary(self._client(), 2)
        assert result["glossary"]["glossary_id"] == 2
        assert result["glossary"]["glossary_name"] == "Common Information Model"
        assert "assets" not in result["glossary"]

    def test_metadata_keys(self):
        result = assemble_glossary(self._client(), 2)
        assert result["resource"] == "glossary"
        assert result["id"] == "2"
        assert result["field_descriptions"] == []
