"""Tests for CLI field-description update command."""

from __future__ import annotations

import json


from katalogue import WriteResult
from katalogue.client.api import ApiError, AuthError
from katalogue_cli.cli.main import cli


def _write_result(data=None):
    return WriteResult(
        ok=True, message="updated", data=data or [{"field_description_id": 7}]
    )


class TestFieldDescriptionUpdate:
    def test_flag_mode_happy_path(self, runner, cli_auth, mock_client):
        mock_client.update.return_value = _write_result()
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "field-description",
                "update",
                "7",
                "--description",
                "New text",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["field_description_id"] == 7

    def test_only_set_flags_sent(self, runner, cli_auth, mock_client):
        mock_client.update.return_value = _write_result()
        runner.invoke(
            cli,
            [*cli_auth, "field-description", "update", "7", "--name", "New Name"],
        )
        opts = mock_client.update.call_args.args[1]
        assert opts.changes == {"field_description_name": "New Name"}
        assert opts.resource_id == 7

    def test_pii_flag_sets_true(self, runner, cli_auth, mock_client):
        mock_client.update.return_value = _write_result()
        runner.invoke(
            cli,
            [*cli_auth, "field-description", "update", "7", "--pii"],
        )
        opts = mock_client.update.call_args.args[1]
        assert opts.changes.get("is_pii") is True

    def test_no_pii_flag_sets_false(self, runner, cli_auth, mock_client):
        mock_client.update.return_value = _write_result()
        runner.invoke(
            cli,
            [*cli_auth, "field-description", "update", "7", "--no-pii"],
        )
        opts = mock_client.update.call_args.args[1]
        assert opts.changes.get("is_pii") is False

    def test_pii_not_provided_absent_from_changes(self, runner, cli_auth, mock_client):
        mock_client.update.return_value = _write_result()
        runner.invoke(
            cli,
            [*cli_auth, "field-description", "update", "7", "--description", "x"],
        )
        opts = mock_client.update.call_args.args[1]
        assert "is_pii" not in opts.changes

    def test_from_file_happy_path(self, runner, cli_auth, mock_client, tmp_path):
        mock_client.update.return_value = _write_result()
        changes = tmp_path / "fields.json"
        changes.write_text('[{"field_description_id": 7, "is_pii": true}]')
        result = runner.invoke(
            cli,
            [*cli_auth, "field-description", "update", "--from-file", str(changes)],
        )
        assert result.exit_code == 0
        opts = mock_client.update.call_args.args[1]
        assert opts.records[0]["field_description_id"] == 7

    def test_missing_id_and_file(self, runner, cli_auth, mock_client):
        result = runner.invoke(cli, [*cli_auth, "field-description", "update"])
        assert result.exit_code == 2

    def test_id_and_file_mutually_exclusive(
        self, runner, cli_auth, mock_client, tmp_path
    ):
        changes = tmp_path / "fields.json"
        changes.write_text('[{"field_description_id": 7}]')
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "field-description",
                "update",
                "7",
                "--from-file",
                str(changes),
            ],
        )
        assert result.exit_code == 2

    def test_auth_error(self, runner, cli_auth, mock_client):
        mock_client.update.side_effect = AuthError("Token expired")
        result = runner.invoke(
            cli,
            [*cli_auth, "field-description", "update", "7", "--description", "x"],
        )
        assert result.exit_code == 1
        assert "Token expired" in result.output

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.update.side_effect = ApiError("Not found")
        result = runner.invoke(
            cli,
            [*cli_auth, "field-description", "update", "7", "--description", "x"],
        )
        assert result.exit_code == 1
        assert "Not found" in result.output
