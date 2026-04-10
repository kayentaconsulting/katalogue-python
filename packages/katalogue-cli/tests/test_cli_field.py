"""Tests for CLI field commands."""

import json

from katalogue_cli.cli.main import cli
from katalogue_sdk.client.api import ApiError


class TestFieldList:
    def test_list_all(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"field_id": 1, "field_name": "user_id", "is_pii": False}
        ]
        result = runner.invoke(cli, [*cli_auth, "field", "list", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["field_name"] == "user_id"

    def test_list_by_dataset(self, runner, cli_auth, mock_client):
        mock_client.list_by_parent.return_value = [
            {"field_id": 1, "field_name": "user_id"}
        ]
        result = runner.invoke(
            cli, [*cli_auth, "field", "list", "--dataset", "1", "--format", "json"]
        )
        assert result.exit_code == 0
        mock_client.list_by_parent.assert_called_once_with("field", "dataset", "1")

    def test_list_where_bool_filters_pii(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"field_id": 1, "field_name": "email", "is_pii": True},
            {"field_id": 2, "field_name": "created_at", "is_pii": False},
        ]
        result = runner.invoke(
            cli,
            [*cli_auth, "field", "list", "--where", "is_pii=true", "--format", "json"],
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert len(parsed) == 1
        assert parsed[0]["field_id"] == 1

    def test_list_where_multiple_conditions_and(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = [
            {"field_id": 1, "field_name": "email", "is_pii": True, "status": "active"},
            {"field_id": 2, "field_name": "age", "is_pii": True, "status": "inactive"},
            {
                "field_id": 3,
                "field_name": "created_at",
                "is_pii": False,
                "status": "active",
            },
        ]
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "field",
                "list",
                "--where",
                "is_pii=true",
                "--where",
                "status=active",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert len(parsed) == 1
        assert parsed[0]["field_id"] == 1

    def test_list_where_with_dataset_parent(self, runner, cli_auth, mock_client):
        mock_client.list_by_parent.return_value = [
            {"field_id": 1, "field_name": "email", "is_pii": True},
            {"field_id": 2, "field_name": "created_at", "is_pii": False},
        ]
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "field",
                "list",
                "--dataset",
                "42",
                "--where",
                "is_pii=true",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        mock_client.list_by_parent.assert_called_once_with("field", "dataset", "42")
        parsed = json.loads(result.output)
        assert len(parsed) == 1
        assert parsed[0]["field_id"] == 1

    def test_empty_results(self, runner, cli_auth, mock_client):
        mock_client.list_resource.return_value = []
        result = runner.invoke(cli, [*cli_auth, "field", "list", "--format", "table"])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.list_resource.side_effect = ApiError("Server error")
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
    def test_happy_path(self, runner, cli_auth, mock_client):
        mock_client.get_resource.return_value = {
            "field_id": 1,
            "field_name": "email",
            "is_pii": True,
        }
        result = runner.invoke(
            cli, [*cli_auth, "field", "get", "1", "--format", "json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output)["field_name"] == "email"

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get_resource.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*cli_auth, "field", "get", "999"])
        assert result.exit_code == 1
        assert "Not found" in result.output
