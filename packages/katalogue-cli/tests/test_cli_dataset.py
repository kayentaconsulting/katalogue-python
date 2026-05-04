"""Tests for CLI dataset-group and dataset commands."""

import json

from katalogue.client.api import ApiError
from katalogue_cli.cli.main import cli


def _options(mock_client):
    return mock_client.get.call_args.args[1]


class TestDatasetGroupList:
    def test_list_all(self, runner, cli_auth, mock_client, catalog_result):
        data = [{"dataset_group_id": 11, "dataset_group_name": "public"}]
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli, [*cli_auth, "dataset-group", "list", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["dataset_group_name"] == "public"
        assert mock_client.get.call_args.args[0] == "dataset_group"

    def test_list_by_datasource(self, runner, cli_auth, mock_client, catalog_result):
        data = [{"dataset_group_id": 11, "dataset_group_name": "public"}]
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "dataset-group",
                "list",
                "--datasource",
                "1",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert _options(mock_client).parent_id == "1"
        mock_client.list_by_parent.assert_not_called()

    def test_filter_contains_passed_to_sdk(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result([], "json")
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "dataset-group",
                "list",
                "--filter",
                "dataset_group_name contains pub",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert _options(mock_client).filters == ["dataset_group_name contains pub"]


class TestDatasetGroupGet:
    def test_happy_path(self, runner, cli_auth, mock_client, catalog_result):
        data = {"dataset_group_id": 11, "dataset_group_name": "public"}
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli, [*cli_auth, "dataset-group", "get", "11", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)["dataset_group_name"] == "public"
        assert _options(mock_client).resource_id == "11"


class TestDatasetList:
    def test_list_all(self, runner, cli_auth, mock_client, catalog_result):
        data = [{"dataset_id": 1, "dataset_name": "users"}]
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(cli, [*cli_auth, "dataset", "list", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["dataset_name"] == "users"
        assert mock_client.get.call_args.args[0] == "dataset"

    def test_list_by_dataset_group(self, runner, cli_auth, mock_client, catalog_result):
        data = [{"dataset_id": 1, "dataset_name": "users"}]
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "dataset",
                "list",
                "--dataset-group",
                "11",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert _options(mock_client).parent_id == "11"
        mock_client.list_by_parent.assert_not_called()


class TestDatasetGet:
    def test_happy_path(self, runner, cli_auth, mock_client, catalog_result):
        data = {"dataset_id": 1, "dataset_name": "users", "dataset_type": "TABLE"}
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli, [*cli_auth, "dataset", "get", "1", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)["dataset_name"] == "users"
        assert _options(mock_client).resource_id == "1"

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*cli_auth, "dataset", "get", "999"])
        assert result.exit_code == 1
        assert "Not found" in result.output
