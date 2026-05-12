"""Unit tests for shared CLI helpers."""

import json
from unittest.mock import patch

import click

from katalogue import CatalogResult, WrittenFile
from katalogue_cli.cli.common import emit_result, filter_option, filter_properties
from katalogue_cli.cli.main import cli

CLI_AUTH = [
    "--client-id",
    "test-id",
    "--client-secret",
    "test-secret",
    "--base-url",
    "https://test.katalogue.se",
]


@click.command()
@filter_option
def _filter_cmd(filters: tuple[str, ...]):
    """Minimal command for testing filter_option."""
    click.echo(json.dumps(list(filters)))


@click.command()
@click.option("--dry-run", is_flag=True)
@click.pass_context
def _emit_files_cmd(ctx: click.Context, dry_run: bool):
    result = CatalogResult(
        data={},
        output_files=[
            WrittenFile(path="out/a.yml"),
            WrittenFile(path="out/b.yml"),
        ],
    )
    emit_result(ctx, result, "json", dry_run=dry_run)


@click.command()
@click.pass_context
def _emit_table_cmd(ctx: click.Context):
    result = CatalogResult(data=[{"id": 1, "name": "CRM"}])
    emit_result(ctx, result, "table")


@click.command()
@click.pass_context
def _emit_no_match_cmd(ctx: click.Context):
    result = CatalogResult(
        data={
            "resource": "dataset_group",
            "id": "26",
            "system": {"system_id": 10, "system_name": "Kayenta Apps"},
            "datasource": {"datasource_id": 10, "datasource_name": "kayenta_apps"},
            "dataset_group": {"dataset_group_id": 26, "dataset_group_name": "stage"},
            "datasets": [],
            "fields": [],
        }
    )
    emit_result(ctx, result, None)


class TestFilterProperties:
    def test_filter_properties_on_list(self):
        rows = [
            {"system_id": 1, "system_name": "Katalogue", "system_type": "Data Catalog"},
            {"system_id": 2, "system_name": "Kayenta", "system_type": "Intranet"},
        ]
        result = filter_properties(rows, ["system_id", "system_name"])
        assert result == [
            {"system_id": 1, "system_name": "Katalogue"},
            {"system_id": 2, "system_name": "Kayenta"},
        ]

    def test_filter_properties_on_dict(self):
        data = {
            "system_id": 1,
            "system_name": "Katalogue",
            "system_type": "Data Catalog",
        }
        result = filter_properties(data, ["system_id", "system_name"])
        assert result == {"system_id": 1, "system_name": "Katalogue"}

    def test_filter_properties_ignores_missing_fields(self):
        rows = [{"system_id": 1, "system_name": "Katalogue"}]
        result = filter_properties(rows, ["system_id", "nonexistent_field"])
        assert result == [{"system_id": 1}]

    def test_filter_properties_none_returns_unchanged(self):
        rows = [{"system_id": 1, "system_name": "Katalogue"}]
        result = filter_properties(rows, None)
        assert result == rows

    def test_filter_properties_empty_list(self):
        result = filter_properties([], ["system_id"])
        assert result == []

    def test_filter_properties_unwraps_resource_key(self):
        wrapped = {
            "systems": [
                {
                    "system_id": 1,
                    "system_name": "Katalogue",
                    "system_type": "Data Catalog",
                }
            ]
        }
        result = filter_properties(wrapped, ["system_id", "system_name"])
        assert result == [{"system_id": 1, "system_name": "Katalogue"}]


class TestFilterOption:
    def test_single_filter_passes_raw_string(self, runner):
        result = runner.invoke(_filter_cmd, ["--filter", "status=active"])
        assert result.exit_code == 0
        assert json.loads(result.output) == ["status=active"]

    def test_multiple_filters_pass_raw_strings(self, runner):
        result = runner.invoke(
            _filter_cmd,
            ["--filter", "is_pii=true", "--filter", 'system.name="CRM"'],
        )
        assert result.exit_code == 0
        assert json.loads(result.output) == ["is_pii=true", 'system.name="CRM"']

    def test_no_filter_flag_produces_empty_tuple(self, runner):
        result = runner.invoke(_filter_cmd, [])
        assert result.exit_code == 0
        assert json.loads(result.output) == []


class TestEmitResult:
    def test_split_files_prints_wrote_paths(self, runner):
        result = runner.invoke(_emit_files_cmd)
        assert result.exit_code == 0
        assert result.output.splitlines() == [
            "Wrote 2 files",
            "out/a.yml",
            "out/b.yml",
        ]

    def test_dry_run_split_files_prints_would_write_paths(self, runner):
        result = runner.invoke(_emit_files_cmd, ["--dry-run"])
        assert result.exit_code == 0
        assert result.output.splitlines() == [
            "Would write 2 files",
            "out/a.yml",
            "out/b.yml",
        ]

    def test_table_format_renders_data_when_sdk_output_absent(self, runner):
        result = runner.invoke(_emit_table_cmd)
        assert result.exit_code == 0
        assert "name" in result.output
        assert "CRM" in result.output

    def test_empty_hierarchical_result_prints_concise_warning(self, runner):
        result = runner.invoke(_emit_no_match_cmd)
        assert result.exit_code == 0
        combined = result.output + getattr(result, "stderr", "")
        assert "No datasets matched the filter for dataset_group 26." in combined
        assert "No files were written." in combined
        assert "{'resource': 'dataset_group'" not in combined


class TestLazyClientResolution:
    """Client credentials are only accessed when an API call is actually made."""

    def test_get_client_not_in_public_api(self):
        """get_client is removed - commands no longer call it directly."""
        import katalogue_cli.cli.common as common

        assert not hasattr(common, "get_client")

    def test_client_created_exactly_once_per_invocation(self, runner, catalog_result):
        """One KatalogueClient instance is shared across SDK calls."""
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.get.return_value = catalog_result([], "json")
            runner.invoke(cli, [*CLI_AUTH, "system", "list"])
        assert MockClient.call_count == 1

    def test_client_not_constructed_without_api_call(self, runner):
        """KatalogueClient is not instantiated when --help is shown."""
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            runner.invoke(cli, [*CLI_AUTH, "system", "--help"])
        MockClient.assert_not_called()
