"""Tests for CLI changelog command."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from katalogue import CatalogResult
from katalogue.client.api import ApiError, AuthError
from katalogue_cli.cli.main import cli

CLI_AUTH = [
    "--client-id",
    "id",
    "--client-secret",
    "secret",
    "--base-url",
    "https://test.katalogue.se",
]

CHANGELOG_DATA = [
    {
        "changelog_id": 1,
        "created_timestamp": "2024-06-01T12:00:00Z",
        "operation": "U",
        "object_name": "system",
        "object_id": 5,
        "changed_by_user_username": "alice",
        "changed_by_user_fullname": "Alice Smith",
        "old_data": None,
        "new_data": None,
    }
]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _changelog_call_kwargs(mock_client):
    return mock_client.get_changelog.call_args


class TestChangelogGet:
    def test_happy_path_json(self, runner, mock_client, catalog_result) -> None:
        mock_client.get_changelog.return_value = catalog_result(CHANGELOG_DATA, "json")
        result = runner.invoke(
            cli, [*CLI_AUTH, "changelog", "system", "5", "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data[0]["changelog_id"] == 1

    def test_happy_path_table_default(self, runner, mock_client) -> None:
        mock_client.get_changelog.return_value = CatalogResult(data=CHANGELOG_DATA)
        result = runner.invoke(cli, [*CLI_AUTH, "changelog", "system", "5"])
        assert result.exit_code == 0, result.output
        assert "alice" in result.output

    def test_object_name_and_id_forwarded(
        self, runner, mock_client, catalog_result
    ) -> None:
        mock_client.get_changelog.return_value = catalog_result([], "json")
        runner.invoke(
            cli, [*CLI_AUTH, "changelog", "dataset", "42", "--format", "json"]
        )
        call = _changelog_call_kwargs(mock_client)
        assert call.args[0] == "dataset"
        assert call.args[1] == 42

    def test_job_routing(self, runner, mock_client, catalog_result) -> None:
        mock_client.get_changelog.return_value = catalog_result(CHANGELOG_DATA, "json")
        result = runner.invoke(
            cli, [*CLI_AUTH, "changelog", "job", "7", "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        call = _changelog_call_kwargs(mock_client)
        assert call.args[0] == "job"
        assert call.args[1] == 7

    def test_from_date_forwarded(self, runner, mock_client, catalog_result) -> None:
        mock_client.get_changelog.return_value = catalog_result([], "json")
        runner.invoke(
            cli,
            [
                *CLI_AUTH,
                "changelog",
                "system",
                "5",
                "--from",
                "2024-01-01",
                "--format",
                "json",
            ],
        )
        assert _changelog_call_kwargs(mock_client).kwargs["from_date"] == "2024-01-01"

    def test_to_date_forwarded(self, runner, mock_client, catalog_result) -> None:
        mock_client.get_changelog.return_value = catalog_result([], "json")
        runner.invoke(
            cli,
            [
                *CLI_AUTH,
                "changelog",
                "system",
                "5",
                "--to",
                "2024-12-31",
                "--format",
                "json",
            ],
        )
        assert _changelog_call_kwargs(mock_client).kwargs["to_date"] == "2024-12-31"

    def test_include_children_forwarded(
        self, runner, mock_client, catalog_result
    ) -> None:
        mock_client.get_changelog.return_value = catalog_result([], "json")
        runner.invoke(
            cli,
            [
                *CLI_AUTH,
                "changelog",
                "system",
                "5",
                "--include-children",
                "--format",
                "json",
            ],
        )
        assert _changelog_call_kwargs(mock_client).kwargs["include_children"] is True

    def test_include_children_false_by_default(
        self, runner, mock_client, catalog_result
    ) -> None:
        mock_client.get_changelog.return_value = catalog_result([], "json")
        runner.invoke(cli, [*CLI_AUTH, "changelog", "system", "5", "--format", "json"])
        assert _changelog_call_kwargs(mock_client).kwargs["include_children"] is False

    def test_filter_forwarded(self, runner, mock_client, catalog_result) -> None:
        mock_client.get_changelog.return_value = catalog_result([], "json")
        runner.invoke(
            cli,
            [
                *CLI_AUTH,
                "changelog",
                "system",
                "5",
                "--filter",
                "operation=U",
                "--format",
                "json",
            ],
        )
        assert _changelog_call_kwargs(mock_client).kwargs["filters"] == ["operation=U"]

    def test_template_forwarded(self, runner, mock_client) -> None:
        mock_client.get_changelog.return_value = CatalogResult(
            data=[], output="# report"
        )
        result = runner.invoke(
            cli,
            [*CLI_AUTH, "changelog", "system", "5", "--template", "changelog-report"],
        )
        assert result.exit_code == 0, result.output
        call = _changelog_call_kwargs(mock_client)
        assert call.kwargs["output"].template == "changelog-report"

    def test_output_file_forwarded(self, runner, mock_client) -> None:
        mock_client.get_changelog.return_value = CatalogResult(
            data=[], output_file="out.json"
        )
        result = runner.invoke(
            cli,
            [
                *CLI_AUTH,
                "changelog",
                "system",
                "5",
                "--output-file",
                "out.json",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        call = _changelog_call_kwargs(mock_client)
        assert call.kwargs["output"].output_file == "out.json"

    def test_auth_error_exits_1(self, runner, mock_client) -> None:
        mock_client.get_changelog.side_effect = AuthError("Unauthorized")
        result = runner.invoke(cli, [*CLI_AUTH, "changelog", "system", "5"])
        assert result.exit_code == 1
        assert "Authentication failed" in result.output

    def test_api_error_exits_1(self, runner, mock_client) -> None:
        mock_client.get_changelog.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*CLI_AUTH, "changelog", "system", "5"])
        assert result.exit_code == 1
        assert "Not found" in result.output

    def test_value_error_becomes_usage_error(self, runner, mock_client) -> None:
        mock_client.get_changelog.side_effect = ValueError("Invalid object_name 'bad'")
        result = runner.invoke(cli, [*CLI_AUTH, "changelog", "bad", "5"])
        assert result.exit_code == 2

    def test_empty_result_exits_0(self, runner, mock_client) -> None:
        mock_client.get_changelog.return_value = CatalogResult(data=[])
        result = runner.invoke(cli, [*CLI_AUTH, "changelog", "system", "5"])
        assert result.exit_code == 0
