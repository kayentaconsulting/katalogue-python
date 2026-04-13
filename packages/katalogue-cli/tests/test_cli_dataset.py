"""Tests for CLI dataset-group and dataset commands."""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from katalogue_cli.cli.main import cli
from katalogue.client.api import ApiError

CLI_AUTH = ["--client-id", "id", "--client-secret", "secret"]


@pytest.fixture
def runner():
    return CliRunner()


class TestDatasetGroupList:
    def test_list_all(self, runner):
        data = [{"dataset_group_id": 11, "dataset_group_name": "public"}]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "dataset-group", "list", "--format", "json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["dataset_group_name"] == "public"

    def test_list_by_datasource(self, runner):
        data = [{"dataset_group_id": 11, "dataset_group_name": "public"}]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_by_parent.return_value = data
            result = runner.invoke(
                cli,
                [
                    *CLI_AUTH,
                    "dataset-group",
                    "list",
                    "--datasource",
                    "1",
                    "--format",
                    "json",
                ],
            )
        assert result.exit_code == 0
        MockClient.return_value.list_by_parent.assert_called_once_with(
            "dataset_group", "datasource", "1"
        )


class TestDatasetGroupGet:
    def test_happy_path(self, runner):
        data = {"dataset_group_id": 11, "dataset_group_name": "public"}
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get_resource.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "dataset-group", "get", "11", "--format", "json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output)["dataset_group_name"] == "public"


class TestDatasetList:
    def test_list_all(self, runner):
        data = [{"dataset_id": 1, "dataset_name": "users"}]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "dataset", "list", "--format", "json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["dataset_name"] == "users"

    def test_list_by_dataset_group(self, runner):
        data = [{"dataset_id": 1, "dataset_name": "users"}]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_by_parent.return_value = data
            result = runner.invoke(
                cli,
                [
                    *CLI_AUTH,
                    "dataset",
                    "list",
                    "--dataset-group",
                    "11",
                    "--format",
                    "json",
                ],
            )
        assert result.exit_code == 0
        MockClient.return_value.list_by_parent.assert_called_once_with(
            "dataset", "dataset_group", "11"
        )


class TestDatasetGet:
    def test_happy_path(self, runner):
        data = {"dataset_id": 1, "dataset_name": "users", "dataset_type": "TABLE"}
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get_resource.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "dataset", "get", "1", "--format", "json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output)["dataset_name"] == "users"

    def test_api_error(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get_resource.side_effect = ApiError("Not found")
            result = runner.invoke(cli, [*CLI_AUTH, "dataset", "get", "999"])
        assert result.exit_code == 1


class TestDatasetGroupChildren:
    def test_lists_datasets_for_dataset_group(self, runner):
        data = [{"dataset_id": 1, "dataset_name": "users"}]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_by_parent.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "dataset-group", "children", "11", "--format", "json"]
            )
        assert result.exit_code == 0
        MockClient.return_value.list_by_parent.assert_called_once_with(
            "dataset", "dataset_group", "11"
        )
        assert json.loads(result.output)[0]["dataset_name"] == "users"

    def test_api_error(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_by_parent.side_effect = ApiError("Not found")
            result = runner.invoke(cli, [*CLI_AUTH, "dataset-group", "children", "11"])
        assert result.exit_code == 1
        assert "Not found" in result.output


class TestDatasetChildren:
    def test_lists_fields_for_dataset(self, runner):
        data = [{"field_id": 1, "field_name": "user_id"}]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_by_parent.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "dataset", "children", "1", "--format", "json"]
            )
        assert result.exit_code == 0
        MockClient.return_value.list_by_parent.assert_called_once_with(
            "field", "dataset", "1"
        )
        assert json.loads(result.output)[0]["field_name"] == "user_id"

    def test_api_error(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_by_parent.side_effect = ApiError("Not found")
            result = runner.invoke(cli, [*CLI_AUTH, "dataset", "children", "1"])
        assert result.exit_code == 1
        assert "Not found" in result.output
