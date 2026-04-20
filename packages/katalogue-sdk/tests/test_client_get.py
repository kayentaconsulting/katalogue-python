"""Tests for KatalogueClient.get() — high-level fetch API."""

import json
import time
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from katalogue.client.api import KatalogueClient
from katalogue.config.settings import Settings

_DRAFTJS = json.dumps({"blocks": [{"text": "Plain text"}], "entityMap": {}})


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
    {"system_id": "sys-001", "system_name": "CDP", "system_type": "source"},
    {"system_id": "sys-002", "system_name": "Analytics", "system_type": "target"},
]


class TestGetRouting:
    def test_no_ids_calls_list_resource(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS) as mock:
            result = client.get("system")
        mock.assert_called_once_with("system")
        assert result == _SYSTEMS

    def test_resource_id_calls_get_resource(self, client):
        record = _SYSTEMS[0]
        with patch.object(client, "get_resource", return_value=record) as mock:
            result = client.get("system", resource_id="sys-001")
        mock.assert_called_once_with("system", "sys-001")
        assert result == record

    def test_parent_id_calls_list_by_parent(self, client):
        rows = [{"field_id": "f-001", "dataset_id": "dt-001"}]
        with patch.object(client, "list_by_parent", return_value=rows) as mock:
            result = client.get("field", parent_id="dt-001")
        mock.assert_called_once_with("field", "dataset", "dt-001")
        assert result == rows

    def test_parent_id_on_top_level_resource_ignored(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS) as mock:
            result = client.get("system", parent_id=999)
        mock.assert_called_once_with("system")
        assert result == _SYSTEMS

    def test_resource_id_and_parent_id_match_returns_record(self, client):
        record = {"field_id": "f-001", "dataset_id": "dt-001"}
        with patch.object(client, "get_resource", return_value=record):
            result = client.get("field", resource_id="f-001", parent_id="dt-001")
        assert result == record

    def test_resource_id_and_parent_id_mismatch_returns_none(self, client):
        record = {"field_id": "f-001", "dataset_id": "dt-002"}
        with patch.object(client, "get_resource", return_value=record):
            result = client.get("field", resource_id="f-001", parent_id="dt-001")
        assert result is None

    def test_resource_id_and_parent_id_top_level_ignores_parent(self, client):
        record = _SYSTEMS[0]
        with patch.object(client, "get_resource", return_value=record):
            result = client.get("system", resource_id="sys-001", parent_id="ignored")
        assert result == record


class TestGetFilter:
    def test_filter_applied_to_list(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", filter={"system_type": "source"})
        assert len(result) == 1
        assert result[0]["system_id"] == "sys-001"

    def test_multiple_filters_and_logic(self, client):
        rows = [
            {"id": 1, "type": "a", "active": True},
            {"id": 2, "type": "a", "active": False},
            {"id": 3, "type": "b", "active": True},
        ]
        with patch.object(client, "list_resource", return_value=rows):
            result = client.get("system", filter={"type": "a", "active": True})
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_no_filter_returns_all(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system")
        assert len(result) == 2


class TestGetFields:
    def test_fields_narrows_columns(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", fields=["system_id", "system_name"])
        assert all("system_type" not in row for row in result)
        assert all("system_id" in row for row in result)


class TestGetSort:
    def test_sort_asc(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", sort=[{"system_name": "asc"}])
        assert result[0]["system_name"] == "Analytics"

    def test_sort_desc(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", sort=[{"system_name": "desc"}])
        assert result[0]["system_name"] == "CDP"


class TestGetFormat:
    def test_format_none_returns_python_object(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", format=None)
        assert isinstance(result, list)

    def test_format_json_returns_string(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", format="json")
        assert isinstance(result, str)
        assert json.loads(result) == _SYSTEMS

    def test_format_compact_returns_compact_string(self, client):
        with patch.object(client, "list_resource", return_value=[{"id": 1}]):
            result = client.get("system", format="compact")
        assert result == '[{"id":1}]'


class TestGetValidation:
    def test_invalid_resource_raises(self, client):
        with pytest.raises(ValueError, match="resource"):
            client.get("ssystem")

    def test_valid_resource_case_insensitive(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("System")
        assert result == _SYSTEMS

    def test_invalid_format_raises(self, client):
        with pytest.raises(ValueError, match="format"):
            client.get("system", format="table")

    def test_format_case_insensitive(self, client):
        with patch.object(client, "list_resource", return_value=[{"id": 1}]):
            result = client.get("system", format="JSON")
        assert isinstance(result, str)

    def test_invalid_sort_direction_raises(self, client):
        with pytest.raises(ValueError, match="sort"):
            client.get("system", sort=[{"system_name": "ascending"}])

    def test_sort_direction_case_insensitive(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system", sort=[{"system_name": "ASC"}])
        assert result[0]["system_name"] == "Analytics"

    def test_int_resource_id_accepted(self, client):
        record = _SYSTEMS[0]
        with patch.object(client, "get_resource", return_value=record) as mock:
            client.get("system", resource_id=1)
        mock.assert_called_once_with("system", 1)

    def test_int_parent_id_accepted(self, client):
        rows = [{"field_id": 1, "dataset_id": 42}]
        with patch.object(client, "list_by_parent", return_value=rows) as mock:
            client.get("field", parent_id=42)
        mock.assert_called_once_with("field", "dataset", 42)


class TestGetFormatDescriptions:
    def test_descriptions_converted_when_flag_set(self, client):
        rows = [{"name": "A", "description": _DRAFTJS}]
        with patch.object(client, "list_resource", return_value=rows):
            result = client.get("system", format_descriptions_as_text=True)
        assert result[0]["description"] == "Plain text"

    def test_descriptions_preserved_when_flag_not_set(self, client):
        rows = [{"name": "A", "description": _DRAFTJS}]
        with patch.object(client, "list_resource", return_value=rows):
            result = client.get("system")
        assert result[0]["description"] == _DRAFTJS
