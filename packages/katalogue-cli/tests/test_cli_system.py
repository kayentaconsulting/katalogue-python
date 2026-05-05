"""Tests for CLI system commands."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from katalogue import CatalogResult, GetOptions, OutputOptions, WrittenFile
from katalogue.client.api import ApiError, AuthError
from katalogue_cli.cli.main import cli

FIXTURES = Path(__file__).parent / "fixtures"

CLI_AUTH = [
    "--client-id",
    "id",
    "--client-secret",
    "secret",
    "--base-url",
    "https://test.katalogue.se",
]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def system_list_data():
    return json.loads((FIXTURES / "system_list.json").read_text())


def _get_options(mock_client) -> GetOptions:
    return mock_client.get.call_args.args[1]


class TestSystemGet:
    def test_happy_path_json(self, runner, mock_client, catalog_result):
        data = {"system_id": 1, "system_name": "Katalogue"}
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli,
            [*CLI_AUTH, "system", "get", "1", "--format", "json"],
        )
        assert result.exit_code == 0
        assert json.loads(result.output)["system_name"] == "Katalogue"
        mock_client.get.assert_called_once()
        assert mock_client.get.call_args.args[0] == "system"
        options = _get_options(mock_client)
        assert options.resource_id == "1"
        assert options.output.format == "json"

    def test_table_uses_cli_renderer_not_sdk_output(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={"system_id": 1, "system_name": "Katalogue"}
        )
        result = runner.invoke(
            cli,
            [*CLI_AUTH, "system", "get", "1", "--format", "table"],
        )
        assert result.exit_code == 0
        assert "system_name" in result.output
        assert "Katalogue" in result.output
        assert _get_options(mock_client).output.format is None

    def test_missing_credentials_shows_error(self, runner, monkeypatch, mocker):
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        mocker.patch("katalogue_cli.cli.common.load_config_file", return_value={})
        mocker.patch("katalogue_cli.cli.common.keyring.get_password", return_value=None)
        result = runner.invoke(cli, ["system", "get", "1"])
        assert result.exit_code == 1
        assert "client" in result.output.lower()

    def test_api_error_shows_message(self, runner, mock_client):
        mock_client.get.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*CLI_AUTH, "system", "get", "bad"])
        assert result.exit_code == 1
        assert "Not found" in result.output

    def test_auth_error_shows_message(self, runner, mock_client):
        mock_client.get.side_effect = AuthError("Unauthorized")
        result = runner.invoke(cli, [*CLI_AUTH, "system", "get", "1"])
        assert result.exit_code == 1
        assert "Authentication failed" in result.output

    def test_include_children_passed_to_sdk(self, runner, mock_client, catalog_result):
        data = {"resource": "system", "system": {"system_id": 1}}
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli, [*CLI_AUTH, "system", "get", "1", "--include-children"]
        )
        assert result.exit_code == 0
        options = _get_options(mock_client)
        assert options.resource_id == "1"
        assert options.include_children is True
        assert options.output.format == "json"

    def test_template_split_dry_run_flags(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={},
            output_files=[WrittenFile(path="out/users.yml")],
        )
        result = runner.invoke(
            cli,
            [
                *CLI_AUTH,
                "system",
                "get",
                "1",
                "--include-children",
                "--template",
                "dbt-source",
                "--split-by",
                "dataset",
                "--output-dir",
                "./out",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert result.output.splitlines() == ["Would write 1 files", "out/users.yml"]
        options = _get_options(mock_client)
        assert options.include_children is True
        assert options.output == OutputOptions(
            format=None,
            template="dbt-source",
            split_by="dataset",
            output_dir="./out",
            dry_run=True,
        )

    def test_template_single_output_file_flags(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={},
            output="version: 2",
            output_file="./out.sql",
        )
        result = runner.invoke(
            cli,
            [
                *CLI_AUTH,
                "system",
                "get",
                "1",
                "--include-children",
                "--template",
                "dbt-source",
                "--output-file",
                "./out.sql",
                "--overwrite",
            ],
        )
        assert result.exit_code == 0
        assert result.output.strip() == "Wrote ./out.sql"
        options = _get_options(mock_client)
        assert options.output.output_file == "./out.sql"
        assert options.output.overwrite is True

    def test_filter_passed_to_sdk(self, runner, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result({"system_id": 1}, "json")
        result = runner.invoke(
            cli,
            [*CLI_AUTH, "system", "get", "1", "--filter", "is_pii=true"],
        )
        assert result.exit_code == 0
        assert _get_options(mock_client).filters == ["is_pii=true"]

    def test_split_by_without_include_children_is_usage_error(
        self, runner, mock_client
    ):
        result = runner.invoke(
            cli,
            [
                *CLI_AUTH,
                "system",
                "get",
                "1",
                "--split-by",
                "dataset",
                "--output-dir",
                "./out",
            ],
        )
        assert result.exit_code == 2
        assert "split_by requires include_children" in result.output
        mock_client.get.assert_not_called()

    def test_split_by_with_output_file_is_usage_error(self, runner, mock_client):
        result = runner.invoke(
            cli,
            [
                *CLI_AUTH,
                "system",
                "get",
                "1",
                "--include-children",
                "--split-by",
                "dataset",
                "--output-file",
                "foo",
            ],
        )
        assert result.exit_code == 2
        assert "split_by cannot be combined with output_file" in result.output
        mock_client.get.assert_not_called()

    def test_malformed_filter_maps_to_usage_error(self, runner, mock_client):
        mock_client.get.side_effect = ValueError(
            "no valid operator found in filter: 'foo bar'"
        )
        result = runner.invoke(
            cli, [*CLI_AUTH, "system", "get", "1", "--filter", "foo bar"]
        )
        assert result.exit_code == 2
        assert "foo bar" in result.output


class TestSystemExport:
    def test_default_writes_json_to_current_dir(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={}, output="{}", output_file="system-1.json"
        )
        result = runner.invoke(cli, [*CLI_AUTH, "system", "export", "1"])
        assert result.exit_code == 0
        assert "system-1.json" in result.output
        options = _get_options(mock_client)
        assert options.include_children is True
        assert options.resource_id == "1"
        assert options.output.format == "json"
        assert options.output.output_file is not None
        assert Path(options.output.output_file).name == "system-1.json"
        assert Path(options.output.output_file).parent == Path(".")

    def test_dry_run_shows_would_write(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={}, output="{}", output_file="system-1.json"
        )
        result = runner.invoke(cli, [*CLI_AUTH, "system", "export", "1", "--dry-run"])
        assert result.exit_code == 0
        assert "Would write" in result.output
        assert "system-1.json" in result.output
        assert _get_options(mock_client).output.dry_run is True

    def test_format_csv_sets_csv_extension(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={}, output="", output_file="system-1.csv"
        )
        result = runner.invoke(
            cli, [*CLI_AUTH, "system", "export", "1", "--format", "csv"]
        )
        assert result.exit_code == 0
        options = _get_options(mock_client)
        assert options.output.format == "csv"
        assert options.output.output_file is not None
        assert Path(options.output.output_file).name == "system-1.csv"

    def test_template_uses_natural_extension(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={}, output="version: 2", output_file="system-1.yml"
        )
        result = runner.invoke(
            cli, [*CLI_AUTH, "system", "export", "1", "--template", "dbt-source"]
        )
        assert result.exit_code == 0
        options = _get_options(mock_client)
        assert options.output.template == "dbt-source"
        assert options.output.format is None
        assert options.output.output_file is not None
        assert Path(options.output.output_file).name == "system-1.yml"

    def test_custom_output_dir(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={}, output="{}", output_file="exports/system-1.json"
        )
        result = runner.invoke(
            cli, [*CLI_AUTH, "system", "export", "1", "--output-dir", "./exports"]
        )
        assert result.exit_code == 0
        options = _get_options(mock_client)
        assert options.output.output_file is not None
        assert Path(options.output.output_file).name == "system-1.json"
        assert Path(options.output.output_file).parent == Path("exports")

    def test_output_file_overrides_auto_name(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={}, output="{}", output_file="./my-export.json"
        )
        result = runner.invoke(
            cli,
            [*CLI_AUTH, "system", "export", "1", "--output-file", "./my-export.json"],
        )
        assert result.exit_code == 0
        assert _get_options(mock_client).output.output_file == "./my-export.json"

    def test_split_by_uses_output_dir(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(
            data={}, output_files=[WrittenFile(path="sales-db.json")]
        )
        result = runner.invoke(
            cli, [*CLI_AUTH, "system", "export", "1", "--split-by", "datasource"]
        )
        assert result.exit_code == 0
        options = _get_options(mock_client)
        assert options.output.split_by == "datasource"
        assert options.output.output_dir == "."
        assert options.output.output_file is None

    def test_auth_error(self, runner, mock_client):
        mock_client.get.side_effect = AuthError("Unauthorized")
        result = runner.invoke(cli, [*CLI_AUTH, "system", "export", "1"])
        assert result.exit_code == 1
        assert "Authentication failed" in result.output

    def test_api_error(self, runner, mock_client):
        mock_client.get.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*CLI_AUTH, "system", "export", "1"])
        assert result.exit_code == 1
        assert "Not found" in result.output


class TestSystemList:
    def test_happy_path_json(
        self, runner, mock_client, catalog_result, system_list_data
    ):
        mock_client.get.return_value = catalog_result(system_list_data, "json")
        result = runner.invoke(cli, [*CLI_AUTH, "system", "list", "--format", "json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert len(parsed) == 3
        options = _get_options(mock_client)
        assert options.resource_id is None
        assert options.output.format == "json"

    def test_happy_path_table_uses_default_fields(
        self, runner, mock_client, system_list_data
    ):
        mock_client.get.return_value = CatalogResult(data=system_list_data)
        result = runner.invoke(cli, [*CLI_AUTH, "system", "list", "--format", "table"])
        assert result.exit_code == 0
        assert "Customer Data Platform" in result.output
        options = _get_options(mock_client)
        assert options.fields == [
            "system_id",
            "system_name",
            "system_type",
            "system_description",
        ]
        assert options.output.format is None

    def test_missing_credentials_shows_error(self, runner, monkeypatch, mocker):
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        mocker.patch("katalogue_cli.cli.common.load_config_file", return_value={})
        mocker.patch("katalogue_cli.cli.common.keyring.get_password", return_value=None)
        result = runner.invoke(cli, ["system", "list"])
        assert result.exit_code == 1
        assert "client" in result.output.lower()

    def test_empty_results_table(self, runner, mock_client):
        mock_client.get.return_value = CatalogResult(data=[])
        result = runner.invoke(cli, [*CLI_AUTH, "system", "list", "--format", "table"])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_empty_results_json(self, runner, mock_client, catalog_result):
        mock_client.get.return_value = catalog_result([], "json")
        result = runner.invoke(cli, [*CLI_AUTH, "system", "list", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == []

    def test_fields_filter_json(self, runner, mock_client, catalog_result):
        data = [
            {"system_id": 1, "system_name": "Katalogue"},
            {"system_id": 2, "system_name": "Kayenta"},
        ]
        mock_client.get.return_value = catalog_result(data, "json")
        result = runner.invoke(
            cli,
            [
                *CLI_AUTH,
                "system",
                "list",
                "--fields",
                "system_id,system_name",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert json.loads(result.output) == data
        assert _get_options(mock_client).fields == ["system_id", "system_name"]

    def test_wide_bypasses_default_fields_for_table(self, runner, mock_client):
        data = [
            {
                "system_id": 1,
                "system_name": "Katalogue",
                "system_type": "Data Catalog",
                "owner": "admin",
            }
        ]
        mock_client.get.return_value = CatalogResult(data=data)
        result = runner.invoke(
            cli, [*CLI_AUTH, "system", "list", "--format", "table", "--wide"]
        )
        assert result.exit_code == 0
        assert "owner" in result.output
        assert _get_options(mock_client).fields is None

    def test_list_compact(self, runner, mock_client, catalog_result):
        data = [
            {"system_id": 1, "system_name": "Katalogue"},
            {"system_id": 2, "system_name": "Kayenta"},
        ]
        mock_client.get.return_value = catalog_result(data, "compact")
        result = runner.invoke(
            cli, [*CLI_AUTH, "system", "list", "--format", "compact"]
        )
        assert result.exit_code == 0
        assert "\n" not in result.output.strip()
        assert len(json.loads(result.output)) == 2

    def test_api_error_shows_message(self, runner, mock_client):
        mock_client.get.side_effect = ApiError("Server error")
        result = runner.invoke(cli, [*CLI_AUTH, "system", "list"])
        assert result.exit_code == 1
        assert "Server error" in result.output

    def test_validation_error_maps_to_usage_error(self, runner, mock_client):
        try:
            GetOptions(output=OutputOptions(split_by="dataset", output_dir="./out"))
        except ValidationError as exc:
            mock_client.get.side_effect = exc
        result = runner.invoke(cli, [*CLI_AUTH, "system", "list"])
        assert result.exit_code == 2
        assert "split_by requires include_children" in result.output


class TestSystemKeys:
    def test_returns_sorted_keys_as_lines(self, runner, mock_client):
        mock_client.list_resource.return_value = [
            {"system_id": 1, "system_name": "X", "active": True}
        ]
        result = runner.invoke(cli, [*CLI_AUTH, "system", "keys"])
        assert result.exit_code == 0
        assert result.output.strip().splitlines() == [
            "active",
            "system_id",
            "system_name",
        ]

    def test_returns_json_array(self, runner, mock_client):
        mock_client.list_resource.return_value = [{"system_id": 1, "system_name": "X"}]
        result = runner.invoke(cli, [*CLI_AUTH, "system", "keys", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == ["system_id", "system_name"]

    def test_empty_list_lines(self, runner, mock_client):
        mock_client.list_resource.return_value = []
        result = runner.invoke(cli, [*CLI_AUTH, "system", "keys"])
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_empty_list_json(self, runner, mock_client):
        mock_client.list_resource.return_value = []
        result = runner.invoke(cli, [*CLI_AUTH, "system", "keys", "--format", "json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == []

    def test_api_error(self, runner, mock_client):
        mock_client.list_resource.side_effect = ApiError("Server error")
        result = runner.invoke(cli, [*CLI_AUTH, "system", "keys"])
        assert result.exit_code == 1
        assert "Server error" in result.output


class TestTopLevelExportRemoved:
    def test_root_help_no_longer_lists_export(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "export" not in result.output

    def test_export_group_is_removed(self, runner):
        result = runner.invoke(cli, [*CLI_AUTH, "export", "system", "1"])
        assert result.exit_code != 0
        assert "No such command" in result.output
