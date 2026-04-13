"""Tests for CLI datasource commands."""

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


class TestDatasourceList:
    def test_list_all(self, runner):
        data = [{"datasource_id": 1, "datasource_name": "katalogue"}]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "datasource", "list", "--format", "json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["datasource_name"] == "katalogue"

    def test_list_by_system(self, runner):
        data = [{"datasource_id": 1, "datasource_name": "katalogue"}]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_by_parent.return_value = data
            result = runner.invoke(
                cli,
                [*CLI_AUTH, "datasource", "list", "--system", "1", "--format", "json"],
            )
        assert result.exit_code == 0
        MockClient.return_value.list_by_parent.assert_called_once_with(
            "datasource", "system", "1"
        )

    def test_empty_results(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = []
            result = runner.invoke(
                cli, [*CLI_AUTH, "datasource", "list", "--format", "table"]
            )
        assert result.exit_code == 0
        assert "No results" in result.output


class TestDatasourceGet:
    def test_happy_path(self, runner):
        data = {
            "datasource_id": 1,
            "datasource_name": "katalogue",
            "datasource_type_name": "PostgreSQL",
        }
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get_resource.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "datasource", "get", "1", "--format", "json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output)["datasource_type_name"] == "PostgreSQL"

    def test_api_error(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get_resource.side_effect = ApiError("Not found")
            result = runner.invoke(cli, [*CLI_AUTH, "datasource", "get", "999"])
        assert result.exit_code == 1
        assert "Not found" in result.output


class TestDatasourceChildren:
    def test_lists_dataset_groups_for_datasource(self, runner):
        data = [{"dataset_group_id": 11, "dataset_group_name": "public"}]
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_by_parent.return_value = data
            result = runner.invoke(
                cli, [*CLI_AUTH, "datasource", "children", "1", "--format", "json"]
            )
        assert result.exit_code == 0
        MockClient.return_value.list_by_parent.assert_called_once_with(
            "dataset_group", "datasource", "1"
        )
        assert json.loads(result.output)[0]["dataset_group_name"] == "public"

    def test_api_error(self, runner):
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_by_parent.side_effect = ApiError("Not found")
            result = runner.invoke(cli, [*CLI_AUTH, "datasource", "children", "1"])
        assert result.exit_code == 1
        assert "Not found" in result.output
