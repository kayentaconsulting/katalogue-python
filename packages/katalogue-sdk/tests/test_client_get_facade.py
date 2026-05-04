"""Additional tests for the new get() facade: strategy metadata, raw envelope, Filter objects, locked paths."""

import time
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from katalogue.client.api import KatalogueClient
from katalogue.config.settings import Settings
from katalogue.filters import Filter
from katalogue.options import GetOptions


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


_SYSTEMS = [
    {"system_id": 1, "system_name": "CRM", "system_type": "source"},
    {"system_id": 2, "system_name": "ERP", "system_type": "target"},
]


class TestStrategyMetadata:
    def test_list_strategy(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system")
        assert result.metadata["strategy"] == "list"

    def test_single_strategy(self, client):
        with patch.object(client, "get_resource", return_value=_SYSTEMS[0]):
            result = client.get("system", GetOptions(resource_id=1))
        assert result.metadata["strategy"] == "single"

    def test_list_by_parent_strategy(self, client):
        rows = [{"dataset_id": 1, "dataset_group_id": 5}]
        with patch.object(client, "list_by_parent", return_value=rows):
            result = client.get("dataset", GetOptions(parent_id=5))
        assert result.metadata["strategy"] == "list_by_parent"


class TestRawEnvelope:
    def test_raw_is_pre_filter_response(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", GetOptions(filters=["system_type=source"]))
        assert result.raw == _SYSTEMS
        assert len(result.data) == 1

    def test_raw_preserved_for_single_record(self, client):
        record = _SYSTEMS[0]
        with patch.object(client, "get_resource", return_value=record):
            result = client.get("system", GetOptions(resource_id=1))
        assert result.raw == record
        assert result.data == record

    def test_output_file_none(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system")
        assert result.output_file is None
        assert result.output_files == []


class TestFilterObjects:
    def test_filter_as_filter_object(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            f = Filter(path="system_type", operator="=", value="source")
            result = client.get("system", GetOptions(filters=[f]))
        assert len(result.data) == 1
        assert result.data[0]["system_name"] == "CRM"

    def test_filter_neq(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", GetOptions(filters=["system_type!=source"]))
        assert len(result.data) == 1
        assert result.data[0]["system_name"] == "ERP"

    def test_filter_string_and_filter_object_equivalent(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            r1 = client.get("system", GetOptions(filters=["system_id=1"]))
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            r2 = client.get(
                "system",
                GetOptions(filters=[Filter(path="system_id", operator="=", value=1)]),
            )
        assert r1.data == r2.data

    def test_invalid_filter_string_raises(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            with pytest.raises(ValueError):
                client.get(
                    "system", GetOptions(filters=["bad string without operator"])
                )


class TestAllOperators:
    def test_gte_filter_works(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", GetOptions(filters=["system_id>=1"]))
        assert len(result.data) == 2

    def test_in_filter_works(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get(
                "system", GetOptions(filters=["system_type in source,target"])
            )
        assert len(result.data) == 2

    def test_not_in_filter_works(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get(
                "system", GetOptions(filters=["system_type not-in csv"])
            )
        assert len(result.data) == 2

    def test_contains_filter_works(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get(
                "system", GetOptions(filters=["system_name contains ER"])
            )
        assert len(result.data) == 1
        assert result.data[0]["system_name"] == "ERP"

    def test_lt_filter_works(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", GetOptions(filters=["system_id<2"]))
        assert len(result.data) == 1
        assert result.data[0]["system_id"] == 1
