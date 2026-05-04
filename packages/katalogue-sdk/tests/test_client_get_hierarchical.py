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
    def test_calls_recursive_and_strategy_is_recursive(self, client):
        client.get_resource = Mock(
            side_effect=[
                {
                    "datasource_id": "ds-1",
                    "datasource_name": "Warehouse",
                    "system_id": "sys-1",
                },
                {"system_id": "sys-1", "system_name": "Finance"},
            ]
        )
        client.list_by_parent = Mock(
            side_effect=[
                [{"dataset_group_id": "dg-1", "dataset_group_name": "public"}],
                [{"dataset_id": "dt-1", "dataset_name": "customers"}],
                [{"field_id": "f-1", "field_name": "email"}],
            ]
        )
        result = client.get(
            "datasource", GetOptions(resource_id="ds-1", include_children=True)
        )
        assert result.metadata["strategy"] == "recursive"

    def test_flat_shape_contains_all_levels(self, client):
        client.get_resource = Mock(
            side_effect=[
                {
                    "datasource_id": "ds-1",
                    "datasource_name": "Warehouse",
                    "system_id": "sys-1",
                },
                {"system_id": "sys-1", "system_name": "Finance"},
            ]
        )
        client.list_by_parent = Mock(
            side_effect=[
                [{"dataset_group_id": "dg-1", "dataset_group_name": "public"}],
                [{"dataset_id": "dt-1", "dataset_name": "customers"}],
                [{"field_id": "f-1", "field_name": "email"}],
            ]
        )
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
        glossary_response = {
            "data": {
                "glossary": {"glossary_id": "gl-1", "glossary_name": "Terms"},
                "terms": [{"name": "Revenue"}],
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
        assert result.data["terms"][0]["name"] == "Revenue"


class TestHierarchicalValidation:
    def test_field_resource_raises_value_error(self, client):
        with pytest.raises(ValueError, match="hierarchical"):
            client.get("field", GetOptions(resource_id="f-1", include_children=True))

    def test_no_resource_id_raises_value_error(self, client):
        with pytest.raises(ValueError, match="resource_id"):
            client.get("system", GetOptions(include_children=True))


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
                    fields=["system", "fields"],
                ),
            )
        # fields param selects top-level keys from the flat dict
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
