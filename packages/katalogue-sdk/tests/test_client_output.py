"""Tests for OutputOptions.format wiring — result.output populated from standard formats."""

import json
import time
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from katalogue.client.api import KatalogueClient
from katalogue.config.settings import Settings
from katalogue.options import GetOptions, OutputOptions


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


class TestOutputFormatWiring:
    def test_no_format_output_is_none(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get("system")
        assert result.output is None

    def test_format_json_populates_output(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get(
                "system", GetOptions(output=OutputOptions(format="json"))
            )
        assert result.output is not None
        assert isinstance(result.output, str)
        assert json.loads(result.output) == _SYSTEMS

    def test_format_compact_populates_output(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get(
                "system", GetOptions(output=OutputOptions(format="compact"))
            )
        assert result.output is not None
        parsed = json.loads(result.output)
        assert parsed == _SYSTEMS
        assert "\n" not in result.output

    def test_format_table_populates_output_string(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get(
                "system", GetOptions(output=OutputOptions(format="table"))
            )
        assert result.output is not None
        assert isinstance(result.output, str)
        assert "CRM" in result.output
        assert "ERP" in result.output

    def test_data_unchanged_when_format_set(self, client):
        with patch.object(client, "list_resource", return_value=_SYSTEMS):
            result = client.get(
                "system", GetOptions(output=OutputOptions(format="json"))
            )
        assert result.data == _SYSTEMS

    def test_single_record_format_json(self, client):
        record = _SYSTEMS[0]
        with patch.object(client, "get_resource", return_value=record):
            result = client.get(
                "system", GetOptions(resource_id=1, output=OutputOptions(format="json"))
            )
        assert result.output is not None
        assert json.loads(result.output) == record

    def test_single_record_no_format_output_none(self, client):
        record = _SYSTEMS[0]
        with patch.object(client, "get_resource", return_value=record):
            result = client.get("system", GetOptions(resource_id=1))
        assert result.output is None

    def test_empty_list_format_json(self, client):
        with patch.object(client, "list_resource", return_value=[]):
            result = client.get(
                "system", GetOptions(output=OutputOptions(format="json"))
            )
        assert result.output == "[]"

    def test_empty_list_format_table(self, client):
        with patch.object(client, "list_resource", return_value=[]):
            result = client.get(
                "system", GetOptions(output=OutputOptions(format="table"))
            )
        assert result.output == "No results."
