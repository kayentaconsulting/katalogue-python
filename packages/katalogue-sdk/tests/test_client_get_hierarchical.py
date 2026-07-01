"""Tests for client.get(..., include_children=True) — hierarchical retrieval."""

import time
from unittest.mock import patch, Mock

import pytest
from pydantic import SecretStr

from katalogue.client.api import KatalogueClient
from katalogue.config.settings import Settings
from katalogue.filters import Filter
from katalogue.options import GetOptions, OutputOptions

NESTED_SYSTEM_EXPORT = {
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


@pytest.fixture
def client():
    with patch("katalogue.client.api.OAuth2Session") as MockSession:
        mock_session = MockSession.return_value
        mock_session.token = {
            "access_token": "mock-token",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }
        settings = Settings(
            client_id="test-id",
            client_secret=SecretStr("test-secret"),
            base_url="https://api.example.com",
            token_url="https://api.example.com/oauth/token",
        )
        return KatalogueClient(settings)


class TestSystemHierarchical:
    def test_calls_get_system_export(self, client):
        with patch.object(
            client, "get_system_export", return_value=NESTED_SYSTEM_EXPORT
        ) as mock:
            result = client.get(
                "system", GetOptions(resource_id="sys-1", include_children=True)
            )
        mock.assert_called_once_with("sys-1")
        assert result.metadata["strategy"] == "export_endpoint"

    def test_data_is_flat_shape(self, client):
        with patch.object(
            client, "get_system_export", return_value=NESTED_SYSTEM_EXPORT
        ):
            result = client.get(
                "system", GetOptions(resource_id="sys-1", include_children=True)
            )
        data = result.data
        assert data["resource"] == "system"
        assert data["id"] == "sys-1"
        assert isinstance(data["datasources"], list)
        assert isinstance(data["fields"], list)

    def test_output_still_none(self, client):
        with patch.object(
            client, "get_system_export", return_value=NESTED_SYSTEM_EXPORT
        ):
            result = client.get(
                "system", GetOptions(resource_id="sys-1", include_children=True)
            )
        assert result.output is None


class TestDatasourceHierarchical:
    def test_uses_system_export_endpoint_and_strategy_is_export_endpoint(self, client):
        client.get_resource = Mock(
            return_value={
                "datasource_id": "ds-1",
                "datasource_name": "Warehouse",
                "system_id": "sys-1",
            }
        )
        with patch.object(
            client, "get_system_export", return_value=NESTED_SYSTEM_EXPORT
        ) as mock_export:
            result = client.get(
                "datasource", GetOptions(resource_id="ds-1", include_children=True)
            )
        mock_export.assert_called_once_with("sys-1")
        assert result.metadata["strategy"] == "export_endpoint"

    def test_flat_shape_contains_all_levels(self, client):
        client.get_resource = Mock(
            return_value={
                "datasource_id": "ds-1",
                "datasource_name": "Warehouse",
                "system_id": "sys-1",
            }
        )
        with patch.object(
            client, "get_system_export", return_value=NESTED_SYSTEM_EXPORT
        ):
            result = client.get(
                "datasource", GetOptions(resource_id="ds-1", include_children=True)
            )
        data = result.data
        assert data["resource"] == "datasource"
        assert data["dataset_groups"][0]["datasource_id"] == "ds-1"
        assert data["datasets"][0]["dataset_group_id"] == "dg-1"
        assert data["fields"][0]["dataset_name"] == "customers"


class TestGlossaryHierarchical:
    def test_calls_get_glossary_export(self, client):
        # The export endpoint wraps the payload as {"export": {"meta", "data"}},
        # with glossary fields flat alongside an "assets" list. assemble_glossary
        # reshapes assets into a recursive business_terms tree.
        glossary_response = {
            "export": {
                "meta": {"katalogue_version": "0.23.0"},
                "data": {
                    "glossary_id": "gl-1",
                    "glossary_name": "Terms",
                    "assets": [
                        {
                            "id": 1,
                            "name": "Revenue",
                            "asset_type": "business_term",
                            "full_path": "",
                        },
                        {
                            "id": 2,
                            "name": "Net Revenue",
                            "asset_type": "field_description",
                            "full_path": "Revenue",
                        },
                    ],
                },
            }
        }
        with patch.object(
            client, "get_glossary_export", return_value=glossary_response
        ) as mock:
            result = client.get(
                "glossary", GetOptions(resource_id="gl-1", include_children=True)
            )
        mock.assert_called_once_with("gl-1")
        assert result.metadata["strategy"] == "export_endpoint"
        assert result.data["glossary"]["glossary_id"] == "gl-1"
        assert result.data["glossary"]["glossary_name"] == "Terms"
        assert "terms" not in result.data
        revenue = result.data["business_terms"][0]
        assert revenue["name"] == "Revenue"
        assert revenue["field_descriptions"][0]["name"] == "Net Revenue"


class TestHierarchicalValidation:
    def test_field_resource_raises_value_error(self, client):
        with pytest.raises(ValueError, match="hierarchical"):
            client.get("field", GetOptions(resource_id="f-1", include_children=True))

    def test_no_resource_id_raises_value_error(self, client):
        with pytest.raises(ValueError, match="resource_id"):
            client.get("system", GetOptions(include_children=True))


class TestGlossarySideGuards:
    """Glossary-side exports support neither templates nor hierarchical filters.

    The SDK is the source of truth: reject both with a clear error rather than
    rendering against the wrong shape (template) or silently ignoring the
    request (filter).
    """

    @pytest.mark.parametrize(
        "resource", ["glossary", "business_term", "field_description"]
    )
    def test_template_rejected(self, client, resource):
        with pytest.raises(ValueError, match="[Tt]emplate"):
            client.get(
                resource,
                GetOptions(
                    resource_id="x-1",
                    include_children=True,
                    output=OutputOptions(template="dbt-source"),
                ),
            )

    @pytest.mark.parametrize(
        "resource", ["glossary", "business_term", "field_description"]
    )
    def test_filters_rejected(self, client, resource):
        with pytest.raises(ValueError, match="[Ff]ilter"):
            client.get(
                resource,
                GetOptions(
                    resource_id="x-1",
                    include_children=True,
                    filters=[Filter(path="is_pii", operator="=", value=True)],
                ),
            )

    def test_guard_does_not_over_trigger(self, client):
        client.get_resource = Mock(
            return_value={"business_term_id": "bt-1", "business_term_name": "Customer"}
        )
        client.list_by_reference_to = Mock(return_value=[])
        result = client.get(
            "business_term",
            GetOptions(resource_id="bt-1", include_children=True),
        )
        assert result.data["resource"] == "business_term"


class TestHierarchicalWithFilters:
    def test_filters_applied_to_flat_shape(self, client):
        with patch.object(
            client, "get_system_export", return_value=NESTED_SYSTEM_EXPORT
        ):
            result = client.get(
                "system",
                GetOptions(
                    resource_id="sys-1",
                    include_children=True,
                    filters=[Filter(path="field.is_pii", operator="=", value=True)],
                ),
            )
        # field f-1 has field_is_pii=True which gets aliased to is_pii=True
        field_ids = [f["field_id"] for f in result.data["fields"]]
        assert "f-1" in field_ids

    def test_dataset_prefix_still_works_in_hierarchical_mode(self, client):
        with patch.object(
            client, "get_system_export", return_value=NESTED_SYSTEM_EXPORT
        ):
            result = client.get(
                "system",
                GetOptions(
                    resource_id="sys-1",
                    include_children=True,
                    filters=[
                        Filter(
                            path="dataset.dataset_name", operator="=", value="customers"
                        )
                    ],
                ),
            )
        dataset_ids = [d["dataset_id"] for d in result.data["datasets"]]
        assert dataset_ids == ["dt-1"]


class TestHierarchicalWithFields:
    def test_fields_applied_to_flat_shape(self, client):
        with patch.object(
            client, "get_system_export", return_value=NESTED_SYSTEM_EXPORT
        ):
            result = client.get(
                "system",
                GetOptions(
                    resource_id="sys-1",
                    include_children=True,
                    properties=["system", "fields"],
                ),
            )
        # properties param selects top-level keys from the flat dict
        data = result.data
        assert "system" in data
        assert "fields" in data
        # resource and id are preserved as metadata
        assert "resource" in data
        assert "id" in data


class TestHierarchicalOutputPipeline:
    def test_split_by_dataset_writes_files(self, client, tmp_path):
        with patch.object(
            client, "get_system_export", return_value=NESTED_SYSTEM_EXPORT
        ):
            result = client.get(
                "system",
                GetOptions(
                    resource_id="sys-1",
                    include_children=True,
                    output=OutputOptions(
                        template="dbt-source",
                        split_by="dataset",
                        output_dir=str(tmp_path),
                    ),
                ),
            )
        assert len(result.output_files) == 1
        written_path = result.output_files[0].path
        assert (tmp_path / "customers.yml").exists()
        assert written_path == str(tmp_path / "customers.yml")

    def test_format_json_sets_output(self, client):
        import json as _json

        with patch.object(
            client, "get_system_export", return_value=NESTED_SYSTEM_EXPORT
        ):
            result = client.get(
                "system",
                GetOptions(
                    resource_id="sys-1",
                    include_children=True,
                    output=OutputOptions(format="json"),
                ),
            )
        assert result.output is not None
        parsed = _json.loads(result.output)
        assert parsed["resource"] == "system"
