"""Tests for CLI field-description commands."""

import json

from katalogue import CatalogResult
from katalogue.client.api import ApiError
from katalogue_cli.cli.main import cli


def _options(mock_client):
    return mock_client.get.call_args.args[1]


class TestFieldDescriptionList:
    def test_list_all(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            [{"field_description_id": 1, "field_description_name": "Customer ID"}],
            "json",
        )
        result = runner.invoke(
            cli, [*cli_auth, "field-description", "list", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["field_description_name"] == "Customer ID"
        assert mock_client.get.call_args.args[0] == "field_description"

    def test_list_by_field(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            [{"field_description_id": 1}], "json"
        )
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "field-description",
                "list",
                "--field",
                "5",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert _options(mock_client).parent_id == "5"

    def test_list_by_business_term_uses_reference(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result(
            [{"field_description_id": 1}], "json"
        )
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "field-description",
                "list",
                "--business-term",
                "8",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        opts = _options(mock_client)
        assert opts.reference_parent_resource == "business_term"
        assert opts.reference_parent_id == "8"

    def test_empty_results(self, runner, cli_auth, mock_client):
        mock_client.get.return_value = CatalogResult(data=[])
        result = runner.invoke(
            cli, [*cli_auth, "field-description", "list", "--format", "table"]
        )
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get.side_effect = ApiError("Server error")
        result = runner.invoke(cli, [*cli_auth, "field-description", "list"])
        assert result.exit_code == 1
        assert "Server error" in result.output


class TestFieldDescriptionGet:
    def test_happy_path(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            {"field_description_id": 167, "field_description_name": "Customer ID"},
            "json",
        )
        result = runner.invoke(
            cli, [*cli_auth, "field-description", "get", "167", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)["field_description_name"] == "Customer ID"
        assert _options(mock_client).resource_id == "167"

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*cli_auth, "field-description", "get", "999"])
        assert result.exit_code == 1
        assert "Not found" in result.output


class TestFieldDescriptionExport:
    def test_export_writes_file(self, runner, cli_auth, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={}, output_file="field_description-167.json"
        )
        result = runner.invoke(cli, [*cli_auth, "field-description", "export", "167"])
        assert result.exit_code == 0
        assert "field_description-167.json" in result.output
        assert _options(mock_client).include_children is True

    def test_export_rejects_template(self, runner, cli_auth, mock_client):
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "field-description",
                "export",
                "167",
                "--template",
                "dbt-source",
            ],
        )
        assert result.exit_code == 2
        assert "no such option" in result.output.lower()


class TestFieldDescriptionKeys:
    def test_returns_sorted_keys_as_lines(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"field_description_id": 1, "field_description_name": "Customer ID"}
        ]
        result = runner.invoke(cli, [*cli_auth, "field-description", "keys"])
        assert result.exit_code == 0
        assert result.output.strip().splitlines() == [
            "field_description_id",
            "field_description_name",
        ]

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.list_resource.side_effect = ApiError("Server error")
        result = runner.invoke(cli, [*cli_auth, "field-description", "keys"])
        assert result.exit_code == 1
        assert "Server error" in result.output
