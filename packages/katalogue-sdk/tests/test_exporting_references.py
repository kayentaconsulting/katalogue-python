"""Tests for the reference assemblers (business_term / field_description exports).

These cover the inverse-FK lookup: given a field description, which physical
fields point at it. Fields must come from the targeted
list_by_parent("field", "field_description", id) endpoint — never from a
full-catalog scan via list_resource("field").
"""

from unittest.mock import Mock

from katalogue.exporting import (
    assemble_business_term_references,
    assemble_field_description_references,
)


class TestAssembleBusinessTermReferences:
    def _client(self, *, fields_by_fd):
        client = Mock()
        client.get_resource = Mock(
            return_value={"business_term_id": "bt-1", "business_term_name": "Customer"}
        )
        client.list_by_reference_to = Mock(
            return_value=[
                {"field_description_id": 100, "field_description_name": "Customer ID"},
                {
                    "field_description_id": 200,
                    "field_description_name": "Customer Name",
                },
            ]
        )
        client.list_by_parent = Mock(
            side_effect=lambda resource, parent, pid: fields_by_fd.get(pid, [])
        )
        return client

    def test_nests_fields_under_each_field_description(self):
        client = self._client(
            fields_by_fd={
                100: [{"field_id": "f-1", "field_name": "cust_id"}],
                200: [
                    {"field_id": "f-2", "field_name": "cust_name"},
                    {"field_id": "f-3", "field_name": "name"},
                ],
            }
        )
        result = assemble_business_term_references(client, "bt-1")
        fds = result["field_descriptions"]
        assert [f["field_name"] for f in fds[0]["fields"]] == ["cust_id"]
        assert [f["field_name"] for f in fds[1]["fields"]] == ["cust_name", "name"]

    def test_metadata_and_term_fields_preserved(self):
        client = self._client(fields_by_fd={100: [], 200: []})
        result = assemble_business_term_references(client, "bt-1")
        assert result["resource"] == "business_term"
        assert result["id"] == "bt-1"
        assert result["business_term_name"] == "Customer"

    def test_field_description_without_id_gets_empty_fields(self):
        client = Mock()
        client.get_resource = Mock(return_value={"business_term_id": "bt-1"})
        client.list_by_reference_to = Mock(
            return_value=[{"field_description_name": "Orphan"}]
        )
        client.list_by_parent = Mock()
        result = assemble_business_term_references(client, "bt-1")
        assert result["field_descriptions"][0]["fields"] == []
        client.list_by_parent.assert_not_called()

    def test_does_not_scan_all_fields(self):
        client = self._client(fields_by_fd={100: [], 200: []})
        assemble_business_term_references(client, "bt-1")
        client.list_resource.assert_not_called()


class TestAssembleFieldDescriptionReferences:
    def _client(self, *, fields, refs):
        client = Mock()
        client.get_resource = Mock(
            return_value={
                "field_description_id": 524,
                "field_description_name": "Customer ID",
            }
        )
        client.list_by_reference_from = Mock(return_value=refs)
        client.list_by_parent = Mock(return_value=fields)
        return client

    def test_fields_come_from_targeted_endpoint(self):
        client = self._client(
            fields=[
                {
                    "field_id": "f-1",
                    "field_name": "cust_id",
                    "field_description_id": 524,
                }
            ],
            refs=[],
        )
        result = assemble_field_description_references(client, 524)
        assert [f["field_name"] for f in result["fields"]] == ["cust_id"]

    def test_linked_business_terms_extracted(self):
        client = self._client(
            fields=[],
            refs=[
                {
                    "to_object_name": "business_term",
                    "to_object_id": 15,
                    "name": "Customer",
                    "glossary_id": 2,
                    "glossary_name": "CIM",
                },
                {"to_object_name": "field_description_value", "to_object_id": 99},
            ],
        )
        result = assemble_field_description_references(client, 524)
        assert len(result["business_terms"]) == 1
        bt = result["business_terms"][0]
        assert bt["business_term_name"] == "Customer"
        assert bt["glossary_name"] == "CIM"

    def test_metadata_preserved(self):
        client = self._client(fields=[], refs=[])
        result = assemble_field_description_references(client, 524)
        assert result["resource"] == "field_description"
        assert result["id"] == "524"
        assert result["field_description_name"] == "Customer ID"

    def test_accepts_string_id_without_coercion(self):
        # Previously coerced via int(resource_id); a non-numeric id must not break.
        client = self._client(fields=[], refs=[])
        result = assemble_field_description_references(client, "fd-abc")
        assert result["id"] == "fd-abc"

    def test_does_not_scan_all_fields(self):
        client = self._client(fields=[], refs=[])
        assemble_field_description_references(client, 524)
        client.list_resource.assert_not_called()
