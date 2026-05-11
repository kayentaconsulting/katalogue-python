"""Tests for CLI business-term update command."""

from __future__ import annotations

import json


from katalogue import WriteResult
from katalogue.client.api import ApiError, AuthError
from katalogue_cli.cli.main import cli


def _write_result(data=None):
    return WriteResult(
        ok=True, message="updated", data=data or [{"business_term_id": 42}]
    )


class TestBusinessTermUpdate:
    def test_flag_mode_happy_path(self, runner, cli_auth, mock_client):
        mock_client.update.return_value = _write_result()
        result = runner.invoke(
            cli,
            [*cli_auth, "business-term", "update", "42", "--description", "New desc"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["business_term_id"] == 42

    def test_flag_mode_only_set_flags_sent(self, runner, cli_auth, mock_client):
        mock_client.update.return_value = _write_result()
        runner.invoke(
            cli,
            [
                *cli_auth,
                "business-term",
                "update",
                "42",
                "--name",
                "New Name",
                "--definition",
                "How calculated",
            ],
        )
        opts = mock_client.update.call_args.args[1]
        assert opts.changes == {
            "business_term_name": "New Name",
            "business_term_definition": "How calculated",
        }
        assert opts.resource_id == 42

    def test_from_file_happy_path(self, runner, cli_auth, mock_client, tmp_path):
        mock_client.update.return_value = _write_result()
        changes = tmp_path / "changes.json"
        changes.write_text(
            '[{"business_term_id": 42, "business_term_description": "A"}]'
        )
        result = runner.invoke(
            cli,
            [*cli_auth, "business-term", "update", "--from-file", str(changes)],
        )
        assert result.exit_code == 0
        opts = mock_client.update.call_args.args[1]
        assert opts.records[0]["business_term_id"] == 42

    def test_from_file_not_found(self, runner, cli_auth, mock_client):
        result = runner.invoke(
            cli,
            [*cli_auth, "business-term", "update", "--from-file", "missing.yml"],
        )
        assert result.exit_code == 2

    def test_missing_id_and_file(self, runner, cli_auth, mock_client):
        result = runner.invoke(cli, [*cli_auth, "business-term", "update"])
        assert result.exit_code == 2

    def test_id_and_file_mutually_exclusive(
        self, runner, cli_auth, mock_client, tmp_path
    ):
        changes = tmp_path / "changes.json"
        changes.write_text('[{"business_term_id": 1}]')
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "business-term",
                "update",
                "42",
                "--from-file",
                str(changes),
            ],
        )
        assert result.exit_code == 2

    def test_auth_error(self, runner, cli_auth, mock_client):
        mock_client.update.side_effect = AuthError("Token expired")
        result = runner.invoke(
            cli,
            [*cli_auth, "business-term", "update", "42", "--description", "x"],
        )
        assert result.exit_code == 1
        assert "Token expired" in result.output

    def test_null_flag_sends_none_in_changes(self, runner, cli_auth, mock_client):
        mock_client.update.return_value = _write_result()
        runner.invoke(
            cli,
            [*cli_auth, "business-term", "update", "42", "--description", "null"],
        )
        opts = mock_client.update.call_args.args[1]
        assert opts.changes == {"business_term_description": None}

    def test_none_flag_sends_none_in_changes(self, runner, cli_auth, mock_client):
        mock_client.update.return_value = _write_result()
        runner.invoke(
            cli,
            [*cli_auth, "business-term", "update", "42", "--description", "none"],
        )
        opts = mock_client.update.call_args.args[1]
        assert opts.changes == {"business_term_description": None}

    def test_empty_string_flag_sends_none_in_changes(
        self, runner, cli_auth, mock_client
    ):
        mock_client.update.return_value = _write_result()
        runner.invoke(
            cli,
            [*cli_auth, "business-term", "update", "42", "--description", ""],
        )
        opts = mock_client.update.call_args.args[1]
        assert opts.changes == {"business_term_description": None}

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.update.side_effect = ApiError("Not found")
        result = runner.invoke(
            cli,
            [*cli_auth, "business-term", "update", "42", "--description", "x"],
        )
        assert result.exit_code == 1
        assert "Not found" in result.output


class TestBusinessTermContinueOnError:
    def _partial_result(self, record_id, ok, message="ok"):
        return WriteResult(ok=ok, message=message, record_id=record_id)

    def test_all_ok_exit_0(self, runner, cli_auth, mock_client, tmp_path):
        mock_client.update.return_value = WriteResult(
            ok=True,
            message="",
            partial_results=[
                self._partial_result(1, True, "1 updated"),
                self._partial_result(4, True, "1 updated"),
            ],
        )
        f = tmp_path / "records.json"
        f.write_text('[{"business_term_id": 1}, {"business_term_id": 4}]')
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "business-term",
                "update",
                "--from-file",
                str(f),
                "--continue-on-error",
            ],
        )
        assert result.exit_code == 0

    def test_any_failure_exit_1(self, runner, cli_auth, mock_client, tmp_path):
        mock_client.update.return_value = WriteResult(
            ok=False,
            message="",
            partial_results=[
                self._partial_result(1, True, "1 updated"),
                self._partial_result(8, False, "backend error"),
            ],
        )
        f = tmp_path / "records.json"
        f.write_text('[{"business_term_id": 1}, {"business_term_id": 8}]')
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "business-term",
                "update",
                "--from-file",
                str(f),
                "--continue-on-error",
            ],
        )
        assert result.exit_code == 1

    def test_shows_per_record_status(self, runner, cli_auth, mock_client, tmp_path):
        mock_client.update.return_value = WriteResult(
            ok=False,
            message="",
            partial_results=[
                self._partial_result(1, True, "1 updated"),
                self._partial_result(8, False, "backend error"),
            ],
        )
        f = tmp_path / "records.json"
        f.write_text('[{"business_term_id": 1}, {"business_term_id": 8}]')
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "business-term",
                "update",
                "--from-file",
                str(f),
                "--continue-on-error",
            ],
            catch_exceptions=False,
        )
        assert "1" in result.output
        assert "8" in result.output
        assert "backend error" in result.output

    def test_continue_on_error_passed_to_sdk(
        self, runner, cli_auth, mock_client, tmp_path
    ):
        mock_client.update.return_value = WriteResult(ok=True, message="ok")
        f = tmp_path / "records.json"
        f.write_text('[{"business_term_id": 1}]')
        runner.invoke(
            cli,
            [
                *cli_auth,
                "business-term",
                "update",
                "--from-file",
                str(f),
                "--continue-on-error",
            ],
        )
        opts = mock_client.update.call_args.args[1]
        assert opts.continue_on_error is True
