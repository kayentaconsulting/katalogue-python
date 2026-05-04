"""Tests for CLI field commands."""

import json

from katalogue import CatalogResult
from katalogue.client.api import ApiError
from katalogue_cli.cli.main import cli


def _options(mock_client):
    return mock_client.get.call_args.args[1]


class TestFieldList:
    def test_list_all(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            [{"field_id": 1, "field_name": "user_id", "is_pii": False}], "json"
        )
        result = runner.invoke(cli, [*cli_auth, "field", "list", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["field_name"] == "user_id"
        assert mock_client.get.call_args.args[0] == "field"

    def test_list_by_dataset(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            [{"field_id": 1, "field_name": "user_id"}], "json"
        )
        result = runner.invoke(
            cli, [*cli_auth, "field", "list", "--dataset", "1", "--format", "json"]
        )
        assert result.exit_code == 0
        assert _options(mock_client).parent_id == "1"
        mock_client.list_by_parent.assert_not_called()

    def test_list_filter_bool_passed_to_sdk(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result(
            [{"field_id": 1, "field_name": "email", "is_pii": True}], "json"
        )
        result = runner.invoke(
            cli,
            [*cli_auth, "field", "list", "--filter", "is_pii=true", "--format", "json"],
        )
        assert result.exit_code == 0
        assert _options(mock_client).filters == ["is_pii=true"]

    def test_list_filter_multiple_conditions_passed_to_sdk(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result([], "json")
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "field",
                "list",
                "--filter",
                "is_pii=true",
                "--filter",
                "status=active",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert _options(mock_client).filters == ["is_pii=true", "status=active"]

    def test_list_filter_with_dataset_parent(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result(
            [{"field_id": 1, "field_name": "email", "is_pii": True}], "json"
        )
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "field",
                "list",
                "--dataset",
                "42",
                "--filter",
                "is_pii=true",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        options = _options(mock_client)
        assert options.parent_id == "42"
        assert options.filters == ["is_pii=true"]

    def test_empty_results(self, runner, cli_auth, mock_client):
        mock_client.get.return_value = CatalogResult(data=[])
        result = runner.invoke(cli, [*cli_auth, "field", "list", "--format", "table"])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get.side_effect = ApiError("Server error")
        result = runner.invoke(cli, [*cli_auth, "field", "list"])
        assert result.exit_code == 1
        assert "Server error" in result.output


class TestFieldKeys:
    def test_returns_sorted_keys_as_lines(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"field_id": 1, "field_name": "email", "is_pii": True}
        ]
        result = runner.invoke(cli, [*cli_auth, "field", "keys"])
        assert result.exit_code == 0
        assert result.output.strip().splitlines() == [
            "field_id",
            "field_name",
            "is_pii",
        ]

    def test_returns_json_array(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"field_id": 1, "field_name": "email"}
        ]
        result = runner.invoke(cli, [*cli_auth, "field", "keys", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == ["field_id", "field_name"]

    def test_empty_list_json(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = []
        result = runner.invoke(cli, [*cli_auth, "field", "keys", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == []

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.list_resource.side_effect = ApiError("Server error")
        result = runner.invoke(cli, [*cli_auth, "field", "keys"])
        assert result.exit_code == 1
        assert "Server error" in result.output


class TestFieldGet:
    def test_happy_path(self, runner, cli_auth, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result(
            {"field_id": 1, "field_name": "email", "is_pii": True}, "json"
        )
        result = runner.invoke(
            cli, [*cli_auth, "field", "get", "1", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)["field_name"] == "email"
        assert _options(mock_client).resource_id == "1"

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*cli_auth, "field", "get", "999"])
        assert result.exit_code == 1
        assert "Not found" in result.output
