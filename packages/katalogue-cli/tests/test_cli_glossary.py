"""Tests for CLI glossary commands."""

import json

from katalogue import CatalogResult, WrittenFile
from katalogue.client.api import ApiError
from katalogue_cli.cli.main import cli


def _options(mock_client):
    return mock_client.get.call_args.args[1]


class TestGlossaryList:
    def test_list_all(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            [{"glossary_id": 1, "glossary_name": "Business Terms"}], "json"
        )
        result = runner.invoke(cli, [*cli_auth, "glossary", "list", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["glossary_name"] == "Business Terms"
        assert mock_client.get.call_args.args[0] == "glossary"

    def test_empty_results(self, runner, cli_auth, mock_client):
        mock_client.get.return_value = CatalogResult(data=[])
        result = runner.invoke(
            cli, [*cli_auth, "glossary", "list", "--format", "table"]
        )
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get.side_effect = ApiError("Server error")
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
    def test_happy_path(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            {
                "glossary_id": 1,
                "glossary_name": "Business Terms",
            },
            "json",
        )
        result = runner.invoke(
            cli, [*cli_auth, "glossary", "get", "1", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)["glossary_name"] == "Business Terms"
        assert _options(mock_client).resource_id == "1"

    def test_include_children_split_output(self, runner, cli_auth, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={},
            output_files=[WrittenFile(path="out/glossary.yml")],
        )
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "glossary",
                "get",
                "1",
                "--include-children",
                "--template",
                "column-mapping",
                "--split-by",
                "dataset",
                "--output-dir",
                "out",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Would write 1 files" in result.output
        assert _options(mock_client).include_children is True

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*cli_auth, "glossary", "get", "999"])
        assert result.exit_code == 1
        assert "Not found" in result.output
