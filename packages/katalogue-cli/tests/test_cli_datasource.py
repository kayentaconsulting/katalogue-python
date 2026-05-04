"""Tests for CLI datasource commands."""

import json

from katalogue import CatalogResult
from katalogue.client.api import ApiError
from katalogue_cli.cli.main import cli


def _options(mock_client):
    return mock_client.get.call_args.args[1]


class TestDatasourceList:
    def test_list_all(self, runner, cli_auth, mock_client, catalog_result):
        data = [{"datasource_id": 1, "datasource_name": "katalogue"}]
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli, [*cli_auth, "datasource", "list", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["datasource_name"] == "katalogue"
        assert mock_client.get.call_args.args[0] == "datasource"
        assert _options(mock_client).parent_id is None

    def test_list_by_system(self, runner, cli_auth, mock_client, catalog_result):
        data = [{"datasource_id": 1, "datasource_name": "katalogue"}]
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli,
            [*cli_auth, "datasource", "list", "--system", "1", "--format", "json"],
        )
        assert result.exit_code == 0
        assert _options(mock_client).parent_id == "1"
        mock_client.list_by_parent.assert_not_called()

    def test_filter_not_equal_passed_to_sdk(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result([], "json")
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "datasource",
                "list",
                "--filter",
                'system.name!="CRM"',
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert _options(mock_client).filters == ['system.name!="CRM"']

    def test_empty_results(self, runner, cli_auth, mock_client):
        mock_client.get.return_value = CatalogResult(data=[])
        result = runner.invoke(
            cli, [*cli_auth, "datasource", "list", "--format", "table"]
        )
        assert result.exit_code == 0
        assert "No results" in result.output


class TestDatasourceGet:
    def test_happy_path(self, runner, cli_auth, mock_client, catalog_result):
        data = {
            "datasource_id": 1,
            "datasource_name": "katalogue",
            "datasource_type_name": "PostgreSQL",
        }
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli, [*cli_auth, "datasource", "get", "1", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)["datasource_type_name"] == "PostgreSQL"
        assert _options(mock_client).resource_id == "1"

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*cli_auth, "datasource", "get", "999"])
        assert result.exit_code == 1
        assert "Not found" in result.output
