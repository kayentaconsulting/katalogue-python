"""Tests for CLI system commands - integration tests using Click CliRunner."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from katalogue_cli.cli.main import cli
from katalogue.client.api import AuthError, ApiError

FIXTURES = Path(__file__).parent / "fixtures"

CLI_AUTH = [
    "--client-id",
    "id",
    "--client-secret",
    "secret",
    "--base-url",
    "https://test.katalogue.se",
]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def system_list_data():
    return json.loads((FIXTURES / "system_list.json").read_text())


class TestSystemGet:
    def test_happy_path_json(self, runner):
        data = {"system_id": 1, "system_name": "Katalogue"}
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get_resource.return_value = data
            result = runner.invoke(
                cli,
                [*CLI_AUTH, "system", "get", "1", "--format", "json"],
            )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["system_name"] == "Katalogue"

    def test_missing_credentials_shows_error(self, runner, monkeypatch):
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        with (
            patch("katalogue_cli.cli.common.load_config_file", return_value={}),
            patch("katalogue_cli.cli.common.keyring.get_password", return_value=None),
        ):
            result = runner.invoke(cli, ["system", "get", "1"])
        assert result.exit_code == 1
        assert "client" in result.output.lower()

    def test_api_error_shows_message(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get_resource.side_effect = ApiError("Not found")
            result = runner.invoke(cli, [*CLI_AUTH, "system", "get", "bad"])
        assert result.exit_code == 1
        assert "Not found" in result.output

    def test_auth_error_shows_message(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get_resource.side_effect = AuthError("Unauthorized")
            result = runner.invoke(cli, [*CLI_AUTH, "system", "get", "1"])
        assert result.exit_code == 1
        assert "Authentication failed" in result.output


class TestSystemList:
    def test_happy_path_json(self, runner, system_list_data):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = system_list_data
            result = runner.invoke(
                cli, [*CLI_AUTH, "system", "list", "--format", "json"]
            )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert len(parsed) == 3

    def test_happy_path_table(self, runner, system_list_data):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = system_list_data
            result = runner.invoke(
                cli, [*CLI_AUTH, "system", "list", "--format", "table"]
            )
        assert result.exit_code == 0
        assert "Customer Data Platform" in result.output

    def test_missing_credentials_shows_error(self, runner, monkeypatch):
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        with (
            patch("katalogue_cli.cli.common.load_config_file", return_value={}),
            patch("katalogue_cli.cli.common.keyring.get_password", return_value=None),
        ):
            result = runner.invoke(cli, ["system", "list"])
        assert result.exit_code == 1
        assert "client" in result.output.lower()

    def test_empty_results(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = []
            result = runner.invoke(
                cli, [*CLI_AUTH, "system", "list", "--format", "table"]
            )
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_fields_filter_json(self, runner):
        data = [
            {"system_id": 1, "system_name": "Katalogue", "system_type": "Data Catalog"},
            {"system_id": 2, "system_name": "Kayenta", "system_type": "Intranet"},
        ]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = data
            result = runner.invoke(
                cli,
                [
                    *CLI_AUTH,
                    "system",
                    "list",
                    "--fields",
                    "system_id,system_name",
                    "--format",
                    "json",
                ],
            )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed == [
            {"system_id": 1, "system_name": "Katalogue"},
            {"system_id": 2, "system_name": "Kayenta"},
        ]

    def test_fields_filter_table(self, runner):
        data = [
            {"system_id": 1, "system_name": "Katalogue", "system_type": "Data Catalog"}
        ]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = data
            result = runner.invoke(
                cli,
                [
                    *CLI_AUTH,
                    "system",
                    "list",
                    "--fields",
                    "system_id,system_name",
                    "--format",
                    "table",
                ],
            )
        assert result.exit_code == 0
        assert "system_name" in result.output
        assert "system_type" not in result.output

    def test_fields_filter_get(self, runner):
        data = {
            "system_id": 1,
            "system_name": "Katalogue",
            "system_type": "Data Catalog",
        }
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get_resource.return_value = data
            result = runner.invoke(
                cli,
                [
                    *CLI_AUTH,
                    "system",
                    "get",
                    "1",
                    "--fields",
                    "system_id,system_name",
                    "--format",
                    "json",
                ],
            )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert "system_type" not in parsed
        assert parsed["system_name"] == "Katalogue"

    def test_list_compact(self, runner):
        data = [
            {"system_id": 1, "system_name": "Katalogue"},
            {"system_id": 2, "system_name": "Kayenta"},
        ]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "system", "list", "--format", "compact"]
            )
        assert result.exit_code == 0
        output = result.output.strip()
        assert "\n" not in output
        parsed = json.loads(output)
        assert len(parsed) == 2

    def test_get_compact(self, runner):
        data = {
            "system_id": 1,
            "system_name": "Katalogue",
            "system_type": "Data Catalog",
        }
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get_resource.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "system", "get", "1", "--format", "compact"]
            )
        assert result.exit_code == 0
        output = result.output.strip()
        assert "\n" not in output
        parsed = json.loads(output)
        assert parsed["system_name"] == "Katalogue"


class TestSystemKeys:
    def test_returns_sorted_keys_as_lines(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = [
                {"system_id": 1, "system_name": "X", "active": True}
            ]
            result = runner.invoke(cli, [*CLI_AUTH, "system", "keys"])
        assert result.exit_code == 0
        assert result.output.strip().splitlines() == [
            "active",
            "system_id",
            "system_name",
        ]

    def test_returns_json_array(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = [
                {"system_id": 1, "system_name": "X"}
            ]
            result = runner.invoke(
                cli, [*CLI_AUTH, "system", "keys", "--format", "json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output) == ["system_id", "system_name"]

    def test_empty_list_lines(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = []
            result = runner.invoke(cli, [*CLI_AUTH, "system", "keys"])
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_empty_list_json(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = []
            result = runner.invoke(
                cli, [*CLI_AUTH, "system", "keys", "--format", "json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output) == []

    def test_api_error(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.side_effect = ApiError("Server error")
            result = runner.invoke(cli, [*CLI_AUTH, "system", "keys"])
        assert result.exit_code == 1
        assert "Server error" in result.output
