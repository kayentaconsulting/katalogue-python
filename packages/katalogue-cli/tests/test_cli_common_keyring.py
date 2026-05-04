"""Tests for keyring fallback in _get_or_create_client (common.py)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from katalogue import CatalogResult
from katalogue_cli.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestKeyringFallback:
    def test_keyring_secret_used_when_no_flag_or_env(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        mocker.patch(
            "katalogue_cli.cli.common.load_config_file",
            return_value={"client_id": "cid", "base_url": "https://test.katalogue.se"},
        )
        mocker.patch(
            "katalogue_cli.cli.common.keyring.get_password",
            return_value="keyring-secret",
        )
        mock_client_cls = mocker.patch("katalogue_cli.cli.common.KatalogueClient")
        mock_client_cls.return_value.get.return_value = CatalogResult(
            data=[], output="[]"
        )

        result = runner.invoke(cli, ["system", "list", "--format", "json"])

        assert result.exit_code == 0
        settings = mock_client_cls.call_args[0][0]
        assert settings.client_secret.get_secret_value() == "keyring-secret"

    def test_keyring_not_consulted_when_flag_secret_provided(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        mock_keyring = mocker.patch("katalogue_cli.cli.common.keyring.get_password")
        mock_client_cls = mocker.patch("katalogue_cli.cli.common.KatalogueClient")
        mock_client_cls.return_value.get.return_value = CatalogResult(
            data=[], output="[]"
        )
        mocker.patch("katalogue_cli.cli.common.load_config_file", return_value={})

        runner.invoke(
            cli,
            [
                "--client-id",
                "cid",
                "--client-secret",
                "flag-secret",
                "system",
                "list",
            ],
        )

        mock_keyring.assert_not_called()

    def test_keyring_not_consulted_when_env_var_secret_provided(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "env-secret")
        mock_keyring = mocker.patch("katalogue_cli.cli.common.keyring.get_password")
        mock_client_cls = mocker.patch("katalogue_cli.cli.common.KatalogueClient")
        mock_client_cls.return_value.get.return_value = CatalogResult(
            data=[], output="[]"
        )
        mocker.patch(
            "katalogue_cli.cli.common.load_config_file",
            return_value={"client_id": "cid"},
        )

        runner.invoke(cli, ["system", "list"])

        mock_keyring.assert_not_called()

    def test_keyring_miss_null_backend_exits_1(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        class NullKeyring:
            pass

        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        mocker.patch(
            "katalogue_cli.cli.common.load_config_file",
            return_value={"client_id": "cid"},
        )
        mocker.patch("katalogue_cli.cli.common.keyring.get_password", return_value=None)
        mocker.patch(
            "katalogue_cli.cli.common.keyring.get_keyring", return_value=NullKeyring()
        )

        result = runner.invoke(cli, ["system", "list"])

        assert result.exit_code == 1
        assert "no keyring backend" in result.output.lower()

    def test_keyring_miss_no_entry_exits_1(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        class SecretService:
            pass

        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        mocker.patch(
            "katalogue_cli.cli.common.load_config_file",
            return_value={"client_id": "cid"},
        )
        mocker.patch("katalogue_cli.cli.common.keyring.get_password", return_value=None)
        mocker.patch(
            "katalogue_cli.cli.common.keyring.get_keyring",
            return_value=SecretService(),
        )

        result = runner.invoke(cli, ["system", "list"])

        assert result.exit_code == 1
        assert "no stored credentials" in result.output.lower()
