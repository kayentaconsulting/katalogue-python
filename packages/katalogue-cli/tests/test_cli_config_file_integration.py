"""Integration tests: config file values reach KatalogueClient via common.py."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from katalogue import CatalogResult
from katalogue_cli.cli.main import cli


@pytest.fixture
def mock_client(mocker):
    mock = mocker.patch("katalogue_cli.cli.common.KatalogueClient")
    mock.return_value.get.return_value = CatalogResult(data=[], output="[]")
    return mock


@pytest.fixture
def mock_config(mocker):
    """Patch load_config_file at the call site in common.py."""
    return mocker.patch("katalogue_cli.cli.common.load_config_file", return_value={})


def _auth_args(client_id="test-id", client_secret="test-secret"):
    return ["--client-id", client_id, "--client-secret", client_secret]


def _settings_from(mock_client_cls):
    """Extract the Settings object passed to KatalogueClient constructor."""
    return mock_client_cls.call_args[0][0]


class TestConfigFilePrecedence:
    def test_cli_flag_beats_config_file_client_id(
        self, runner: CliRunner, mock_client, mocker
    ) -> None:
        mocker.patch(
            "katalogue_cli.cli.common.load_config_file",
            return_value={
                "client_id": "file-id",
                "base_url": "https://test.katalogue.se",
            },
        )
        runner.invoke(cli, [*_auth_args(client_id="flag-id"), "system", "list"])
        assert _settings_from(mock_client).client_id == "flag-id"

    def test_config_file_client_id_used_when_no_flag(
        self, runner: CliRunner, mock_client, mocker, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        mocker.patch(
            "katalogue_cli.cli.common.load_config_file",
            return_value={
                "client_id": "file-id",
                "base_url": "https://test.katalogue.se",
            },
        )
        result = runner.invoke(cli, ["--client-secret", "secret", "system", "list"])
        assert result.exit_code == 0
        assert _settings_from(mock_client).client_id == "file-id"

    def test_env_var_beats_config_file(
        self, runner: CliRunner, mock_client, mocker, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "env-id")
        mocker.patch(
            "katalogue_cli.cli.common.load_config_file",
            return_value={
                "client_id": "file-id",
                "base_url": "https://test.katalogue.se",
            },
        )
        runner.invoke(cli, ["--client-secret", "secret", "system", "list"])
        assert _settings_from(mock_client).client_id == "env-id"

    def test_config_file_base_url_used(
        self, runner: CliRunner, mock_client, mocker, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_URL", raising=False)
        mocker.patch(
            "katalogue_cli.cli.common.load_config_file",
            return_value={"base_url": "https://from-file.example.com"},
        )
        runner.invoke(cli, [*_auth_args(), "system", "list"])
        assert _settings_from(mock_client).base_url == "https://from-file.example.com"

    def test_config_file_token_url_used(
        self, runner: CliRunner, mock_client, mocker, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_URL", raising=False)
        monkeypatch.delenv("KATALOGUE_TOKEN_URL", raising=False)
        mocker.patch(
            "katalogue_cli.cli.common.load_config_file",
            return_value={
                "base_url": "https://from-file.example.com",
                "token_url": "https://from-file.example.com/oidc/token",
            },
        )
        runner.invoke(cli, [*_auth_args(), "system", "list"])
        assert (
            _settings_from(mock_client).token_url
            == "https://from-file.example.com/oidc/token"
        )

    def test_empty_config_file_still_works_with_flags(
        self,
        runner: CliRunner,
        mock_client,
        mock_config,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("KATALOGUE_URL", "https://test.katalogue.se")
        result = runner.invoke(cli, [*_auth_args(), "system", "list"])
        assert result.exit_code == 0


class TestConfigFileNoFlagsNoEnv:
    def test_command_succeeds_with_only_config_file_credentials(
        self, runner: CliRunner, mock_client, mocker, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        mocker.patch(
            "katalogue_cli.cli.common.load_config_file",
            return_value={
                "client_id": "file-id",
                "base_url": "https://test.katalogue.se",
            },
        )
        # Still needs client_secret from somewhere; provide via env
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "env-secret")
        result = runner.invoke(cli, ["system", "list"])
        assert result.exit_code == 0
        assert _settings_from(mock_client).client_id == "file-id"

    def test_command_fails_when_no_credentials_anywhere(
        self, runner: CliRunner, mock_client, mocker, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        mocker.patch("katalogue_cli.cli.common.load_config_file", return_value={})
        result = runner.invoke(cli, ["system", "list"])
        assert result.exit_code == 1


class TestConfigFileLoadCalledOnce:
    def test_load_config_file_called_once_per_invocation(
        self, runner: CliRunner, mock_client, mocker
    ) -> None:
        mock_load = mocker.patch(
            "katalogue_cli.cli.common.load_config_file", return_value={}
        )
        runner.invoke(cli, [*_auth_args(), "system", "list"])
        assert mock_load.call_count == 1
