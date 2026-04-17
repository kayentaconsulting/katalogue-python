"""Unit tests for shared CLI helpers - filter_fields, parse_where_value, where_option."""

import json
from unittest.mock import patch

import click

from katalogue_cli.cli.common import filter_fields, parse_where_value, where_option
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
@where_option
def _where_cmd(where):
    """Minimal command for testing where_option callback."""
    click.echo(json.dumps([[k, v] for k, v in where]))


class TestFilterFields:
    def test_filter_fields_on_list(self):
        rows = [
            {"system_id": 1, "system_name": "Katalogue", "system_type": "Data Catalog"},
            {"system_id": 2, "system_name": "Kayenta", "system_type": "Intranet"},
        ]
        result = filter_fields(rows, ["system_id", "system_name"])
        assert result == [
            {"system_id": 1, "system_name": "Katalogue"},
            {"system_id": 2, "system_name": "Kayenta"},
        ]

    def test_filter_fields_on_dict(self):
        data = {
            "system_id": 1,
            "system_name": "Katalogue",
            "system_type": "Data Catalog",
        }
        result = filter_fields(data, ["system_id", "system_name"])
        assert result == {"system_id": 1, "system_name": "Katalogue"}

    def test_filter_fields_ignores_missing_fields(self):
        rows = [{"system_id": 1, "system_name": "Katalogue"}]
        result = filter_fields(rows, ["system_id", "nonexistent_field"])
        assert result == [{"system_id": 1}]

    def test_filter_fields_none_returns_unchanged(self):
        rows = [{"system_id": 1, "system_name": "Katalogue"}]
        result = filter_fields(rows, None)
        assert result == rows

    def test_filter_fields_empty_list(self):
        result = filter_fields([], ["system_id"])
        assert result == []

    def test_filter_fields_unwraps_resource_key(self):
        """Wrapped response like {"systems": [...]} is unwrapped when fields are requested."""
        wrapped = {
            "systems": [
                {
                    "system_id": 1,
                    "system_name": "Katalogue",
                    "system_type": "Data Catalog",
                }
            ]
        }
        result = filter_fields(wrapped, ["system_id", "system_name"])
        assert result == [{"system_id": 1, "system_name": "Katalogue"}]


class TestParseWhereValue:
    def test_true_lowercase(self):
        assert parse_where_value("true") is True

    def test_true_mixed_case(self):
        assert parse_where_value("True") is True
        assert parse_where_value("TRUE") is True

    def test_false_lowercase(self):
        assert parse_where_value("false") is False

    def test_false_mixed_case(self):
        assert parse_where_value("False") is False
        assert parse_where_value("FALSE") is False

    def test_digit_string_returns_int(self):
        result = parse_where_value("42")
        assert result == 42
        assert isinstance(result, int)

    def test_zero_returns_int(self):
        result = parse_where_value("0")
        assert result == 0
        assert isinstance(result, int)

    def test_plain_string_unchanged(self):
        result = parse_where_value("TEXT")
        assert result == "TEXT"
        assert isinstance(result, str)

    def test_mixed_alphanumeric_stays_str(self):
        assert parse_where_value("v2") == "v2"

    def test_decimal_stays_str(self):
        result = parse_where_value("3.14")
        assert result == "3.14"
        assert isinstance(result, str)

    def test_leading_zero_integer_coerces(self):
        # "007" coerces to int 7, not string "007" — document this known behaviour
        assert parse_where_value("007") == 7
        assert isinstance(parse_where_value("007"), int)


class TestWhereOptionCallback:
    def test_single_string_value(self, runner):
        result = runner.invoke(_where_cmd, ["--where", "status=active"])
        assert result.exit_code == 0
        assert json.loads(result.output) == [["status", "active"]]

    def test_single_bool_true(self, runner):
        result = runner.invoke(_where_cmd, ["--where", "is_pii=true"])
        assert result.exit_code == 0
        assert json.loads(result.output) == [["is_pii", True]]

    def test_single_bool_false(self, runner):
        result = runner.invoke(_where_cmd, ["--where", "is_pii=false"])
        assert result.exit_code == 0
        assert json.loads(result.output) == [["is_pii", False]]

    def test_single_int_value(self, runner):
        result = runner.invoke(_where_cmd, ["--where", "dataset_id=7"])
        assert result.exit_code == 0
        assert json.loads(result.output) == [["dataset_id", 7]]

    def test_multiple_flags_produce_list(self, runner):
        result = runner.invoke(
            _where_cmd, ["--where", "is_pii=true", "--where", "dataset_id=7"]
        )
        assert result.exit_code == 0
        assert json.loads(result.output) == [["is_pii", True], ["dataset_id", 7]]

    def test_no_where_flag_produces_empty(self, runner):
        result = runner.invoke(_where_cmd, [])
        assert result.exit_code == 0
        assert json.loads(result.output) == []

    def test_missing_equals_sign_raises_usage_error(self, runner):
        result = runner.invoke(_where_cmd, ["--where", "is_pii"])
        assert result.exit_code != 0
        assert "KEY=VALUE" in result.output

    def test_empty_value_is_str(self, runner):
        result = runner.invoke(_where_cmd, ["--where", "status="])
        assert result.exit_code == 0
        assert json.loads(result.output) == [["status", ""]]


class TestLazyClientResolution:
    """Client credentials are only accessed when an API call is actually made."""

    def test_get_client_not_in_public_api(self):
        """get_client is removed — commands no longer call it directly."""
        import katalogue_cli.cli.common as common

        assert not hasattr(common, "get_client")

    def test_client_created_exactly_once_per_invocation(self, runner):
        """One KatalogueClient instance is shared across handle_api_call calls."""
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            MockClient.return_value.list_resource.return_value = []
            runner.invoke(cli, [*CLI_AUTH, "system", "list"])
        assert MockClient.call_count == 1

    def test_client_not_constructed_without_api_call(self, runner):
        """KatalogueClient is not instantiated when --help is shown (no API call)."""
        with patch("katalogue_cli.cli.common.KatalogueClient") as MockClient:
            runner.invoke(cli, [*CLI_AUTH, "system", "--help"])
        MockClient.assert_not_called()
