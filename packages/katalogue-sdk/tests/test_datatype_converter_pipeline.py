"""Integration tests: type mapping enriches fields in the SDK pipeline."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from katalogue.client.api import KatalogueClient
from katalogue.config.settings import Settings
from katalogue.options import GetOptions

_EXPORT = {
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
                            "dataset_group_name": "dbo",
                            "datasets": [
                                {
                                    "dataset_id": "dt-1",
                                    "dataset_name": "orders",
                                    "fields": [
                                        {
                                            "field_id": "f-1",
                                            "field_name": "amount",
                                            "field_datatype": "DECIMAL(10,2)",
                                        },
                                        {
                                            "field_id": "f-2",
                                            "field_name": "description",
                                            "field_datatype": "VARCHAR(500)",
                                        },
                                        {
                                            "field_id": "f-3",
                                            "field_name": "flags",
                                            "field_datatype": "UNKNOWN_TYPE",
                                        },
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


def test_datatype_converter_enriches_fields(client):
    with patch.object(client, "get_system_export", return_value=_EXPORT):
        result = client.get(
            "system",
            GetOptions(
                resource_id="sys-1",
                include_children=True,
                datatype_converter="sqlserver-to-databricks",
            ),
        )
    fields = {f["field_name"]: f for f in result.data["fields"]}
    assert fields["amount"]["datatype_converted"] == "DECIMAL(10,2)"
    assert fields["description"]["datatype_converted"] == "STRING"
    assert fields["flags"]["datatype_converted"] == "UNKNOWN_TYPE"  # passthrough


def test_datatype_converter_not_set_leaves_no_datatype_converted(client):
    with patch.object(client, "get_system_export", return_value=_EXPORT):
        result = client.get(
            "system",
            GetOptions(resource_id="sys-1", include_children=True),
        )
    for field in result.data["fields"]:
        assert "datatype_converted" not in field


def test_get_options_datatype_converter_field():
    opts = GetOptions(datatype_converter="sqlserver-to-databricks")
    assert opts.datatype_converter == "sqlserver-to-databricks"


def test_get_options_datatype_converter_defaults_none():
    opts = GetOptions()
    assert opts.datatype_converter is None
