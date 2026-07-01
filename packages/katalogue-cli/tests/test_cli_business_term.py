"""Tests for CLI business-term commands."""

import json

from katalogue import CatalogResult
from katalogue.client.api import ApiError
from katalogue_cli.cli.main import cli


def _options(mock_client):
    return mock_client.get.call_args.args[1]


class TestBusinessTermList:
    def test_list_all(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            [{"business_term_id": 1, "business_term_name": "Customer"}], "json"
        )
        result = runner.invoke(
            cli, [*cli_auth, "business-term", "list", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["business_term_name"] == "Customer"
        assert mock_client.get.call_args.args[0] == "business_term"

    def test_list_by_glossary(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            [{"business_term_id": 1, "business_term_name": "Customer"}], "json"
        )
        result = runner.invoke(
            cli,
            [*cli_auth, "business-term", "list", "--glossary", "2", "--format", "json"],
        )
        assert result.exit_code == 0
        assert _options(mock_client).parent_id == "2"

    def test_list_filter_passed_to_sdk(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result([], "json")
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "business-term",
                "list",
                "--filter",
                "business_term_name=Customer",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert _options(mock_client).filters == ["business_term_name=Customer"]

    def test_empty_results(self, runner, cli_auth, mock_client):
        mock_client.get.return_value = CatalogResult(data=[])
        result = runner.invoke(
            cli, [*cli_auth, "business-term", "list", "--format", "table"]
        )
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get.side_effect = ApiError("Server error")
        result = runner.invoke(cli, [*cli_auth, "business-term", "list"])
        assert result.exit_code == 1
        assert "Server error" in result.output


class TestBusinessTermGet:
    def test_happy_path(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            {"business_term_id": 8, "business_term_name": "Customer"}, "json"
        )
        result = runner.invoke(
            cli, [*cli_auth, "business-term", "get", "8", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)["business_term_name"] == "Customer"
        assert _options(mock_client).resource_id == "8"

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*cli_auth, "business-term", "get", "999"])
        assert result.exit_code == 1
        assert "Not found" in result.output


class TestBusinessTermExport:
    def test_export_writes_file(self, runner, cli_auth, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={}, output_file="business_term-8.json"
        )
        result = runner.invoke(cli, [*cli_auth, "business-term", "export", "8"])
        assert result.exit_code == 0
        assert "business_term-8.json" in result.output
        assert _options(mock_client).include_children is True

    def test_export_rejects_template(self, runner, cli_auth, mock_client):
        result = runner.invoke(
            cli, [*cli_auth, "business-term", "export", "8", "--template", "dbt-source"]
        )
        assert result.exit_code == 2
        assert "no such option" in result.output.lower()


class TestBusinessTermKeys:
    def test_returns_sorted_keys_as_lines(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"business_term_id": 1, "business_term_name": "Customer"}
        ]
        result = runner.invoke(cli, [*cli_auth, "business-term", "keys"])
        assert result.exit_code == 0
        assert result.output.strip().splitlines() == [
            "business_term_id",
            "business_term_name",
        ]

    def test_returns_json_array(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"business_term_id": 1, "business_term_name": "Customer"}
        ]
        result = runner.invoke(
            cli, [*cli_auth, "business-term", "keys", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output) == ["business_term_id", "business_term_name"]

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.list_resource.side_effect = ApiError("Server error")
        result = runner.invoke(cli, [*cli_auth, "business-term", "keys"])
        assert result.exit_code == 1
        assert "Server error" in result.output
