"""Tests for CLI glossary commands."""

import json

from katalogue_cli.cli.main import cli
from katalogue_sdk.client.api import ApiError


class TestGlossaryList:
    def test_list_all(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"glossary_id": 1, "glossary_name": "Business Terms"}
        ]
        result = runner.invoke(cli, [*cli_auth, "glossary", "list", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["glossary_name"] == "Business Terms"

    def test_empty_results(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = []
        result = runner.invoke(
            cli, [*cli_auth, "glossary", "list", "--format", "table"]
        )
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.list_resource.side_effect = ApiError("Server error")
        result = runner.invoke(cli, [*cli_auth, "glossary", "list"])
        assert result.exit_code == 1
        assert "Server error" in result.output


class TestGlossaryKeys:
    def test_returns_sorted_keys_as_lines(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"glossary_id": 1, "glossary_name": "Business Terms"}
        ]
        result = runner.invoke(cli, [*cli_auth, "glossary", "keys"])
        assert result.exit_code == 0
        assert result.output.strip().splitlines() == ["glossary_id", "glossary_name"]

    def test_returns_json_array(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"glossary_id": 1, "glossary_name": "Business Terms"}
        ]
        result = runner.invoke(cli, [*cli_auth, "glossary", "keys", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == ["glossary_id", "glossary_name"]

    def test_empty_list_json(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = []
        result = runner.invoke(cli, [*cli_auth, "glossary", "keys", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == []


class TestGlossaryGet:
    def test_happy_path(self, runner, cli_auth, mock_client):
        mock_client.get_resource.return_value = {
            "glossary_id": 1,
            "glossary_name": "Business Terms",
        }
        result = runner.invoke(
            cli, [*cli_auth, "glossary", "get", "1", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)["glossary_name"] == "Business Terms"

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get_resource.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*cli_auth, "glossary", "get", "999"])
        assert result.exit_code == 1
        assert "Not found" in result.output
