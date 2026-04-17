"""Tests for `katalogue auth` commands: login, status, logout."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from katalogue_cli.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


def _usable_keyring():
    """A fake keyring backend whose type name is not Keyring or NullKeyring."""

    class SecretService:
        pass

    return SecretService()


def _null_keyring():
    class NullKeyring:
        pass

    return NullKeyring()


class TestAuthLogin:
    def test_flags_happy_path(self, runner: CliRunner, mocker) -> None:
        mocker.patch(
            "katalogue_cli.cli.auth.keyring.get_keyring", return_value=_usable_keyring()
        )
        mock_set = mocker.patch("katalogue_cli.cli.auth.keyring.set_password")
        mock_write = mocker.patch("katalogue_cli.cli.auth.write_config_file")
        mock_client_cls = mocker.patch("katalogue_cli.cli.auth.KatalogueClient")
        mock_client_cls.return_value.list_resource.return_value = []

        result = runner.invoke(
            cli,
            [
                "auth",
                "login",
                "--client-id",
                "cid",
                "--client-secret",
                "csecret",
                "--base-url",
                "https://x.example.com",
                "--token-url",
                "https://x.example.com/oidc/token",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Logged in" in result.output
        mock_set.assert_called_once_with("katalogue", "cid", "csecret")
        call_kwargs = mock_write.call_args.kwargs
        assert call_kwargs.get("client_id") == "cid"
        assert "client_secret" not in call_kwargs

    def test_prompts_happy_path(self, runner: CliRunner, mocker) -> None:
        mocker.patch(
            "katalogue_cli.cli.auth.keyring.get_keyring", return_value=_usable_keyring()
        )
        mock_set = mocker.patch("katalogue_cli.cli.auth.keyring.set_password")
        mocker.patch("katalogue_cli.cli.auth.write_config_file")
        mock_client_cls = mocker.patch("katalogue_cli.cli.auth.KatalogueClient")
        mock_client_cls.return_value.list_resource.return_value = []

        result = runner.invoke(
            cli,
            ["auth", "login"],
            input="cid\ncsecret\nhttps://my.katalogue.se\n\n",
        )

        assert result.exit_code == 0, result.output
        assert "Logged in" in result.output
        mock_set.assert_called_once_with("katalogue", "cid", "csecret")

    def test_null_keyring_exits_before_validation(
        self, runner: CliRunner, mocker
    ) -> None:
        mocker.patch(
            "katalogue_cli.cli.auth.keyring.get_keyring", return_value=_null_keyring()
        )
        mock_client_cls = mocker.patch("katalogue_cli.cli.auth.KatalogueClient")
        mock_write = mocker.patch("katalogue_cli.cli.auth.write_config_file")
        mock_set = mocker.patch("katalogue_cli.cli.auth.keyring.set_password")

        result = runner.invoke(
            cli,
            [
                "auth",
                "login",
                "--client-id",
                "cid",
                "--client-secret",
                "csecret",
            ],
        )

        assert result.exit_code == 1
        assert "no keychain backend" in result.output
        mock_client_cls.assert_not_called()
        mock_write.assert_not_called()
        mock_set.assert_not_called()

    def test_bad_credentials_exits_writes_nothing(
        self, runner: CliRunner, mocker
    ) -> None:
        from katalogue.client.api import AuthError

        mocker.patch(
            "katalogue_cli.cli.auth.keyring.get_keyring", return_value=_usable_keyring()
        )
        mock_client_cls = mocker.patch("katalogue_cli.cli.auth.KatalogueClient")
        mock_client_cls.return_value.list_resource.side_effect = AuthError(
            "invalid_client"
        )
        mock_write = mocker.patch("katalogue_cli.cli.auth.write_config_file")
        mock_set = mocker.patch("katalogue_cli.cli.auth.keyring.set_password")

        result = runner.invoke(
            cli,
            [
                "auth",
                "login",
                "--client-id",
                "bad",
                "--client-secret",
                "wrong",
                "--base-url",
                "https://my.katalogue.se",
            ],
        )

        assert result.exit_code == 1
        mock_write.assert_not_called()
        mock_set.assert_not_called()

    def test_base_url_prompted_when_not_set(self, runner: CliRunner, mocker) -> None:
        mocker.patch(
            "katalogue_cli.cli.auth.keyring.get_keyring", return_value=_usable_keyring()
        )
        mocker.patch("katalogue_cli.cli.auth.keyring.set_password")
        mocker.patch("katalogue_cli.cli.auth.write_config_file")
        mock_client_cls = mocker.patch("katalogue_cli.cli.auth.KatalogueClient")
        mock_client_cls.return_value.list_resource.return_value = []

        result = runner.invoke(
            cli, ["auth", "login"], input="cid\ncsecret\nhttps://my.katalogue.se\n\n"
        )

        assert "Base URL" in result.output

    def test_flags_bypass_prompts(self, runner: CliRunner, mocker) -> None:
        mocker.patch(
            "katalogue_cli.cli.auth.keyring.get_keyring", return_value=_usable_keyring()
        )
        mocker.patch("katalogue_cli.cli.auth.keyring.set_password")
        mocker.patch("katalogue_cli.cli.auth.write_config_file")
        mock_client_cls = mocker.patch("katalogue_cli.cli.auth.KatalogueClient")
        mock_client_cls.return_value.list_resource.return_value = []

        result = runner.invoke(
            cli,
            [
                "auth",
                "login",
                "--client-id",
                "cid",
                "--client-secret",
                "csecret",
                "--base-url",
                "https://x.example.com",
                "--token-url",
                "https://x.example.com/oidc/token",
            ],
        )

        assert result.exit_code == 0
        assert "Client ID:" not in result.output
        assert "Client Secret:" not in result.output

    def test_client_secret_goes_directly_to_keyring(
        self, runner: CliRunner, mocker
    ) -> None:
        mocker.patch(
            "katalogue_cli.cli.auth.keyring.get_keyring", return_value=_usable_keyring()
        )
        mock_set = mocker.patch("katalogue_cli.cli.auth.keyring.set_password")
        mocker.patch("katalogue_cli.cli.auth.write_config_file")
        mock_client_cls = mocker.patch("katalogue_cli.cli.auth.KatalogueClient")
        mock_client_cls.return_value.list_resource.return_value = []

        runner.invoke(
            cli,
            [
                "auth",
                "login",
                "--client-id",
                "cid",
                "--client-secret",
                "csecret",
                "--base-url",
                "https://x.example.com",
                "--token-url",
                "https://x.example.com/oidc/token",
            ],
        )

        mock_set.assert_called_once_with("katalogue", "cid", "csecret")


class TestAuthStatus:
    def test_all_credentials_present_exits_0(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        mocker.patch(
            "katalogue_cli.cli.auth.load_config_file", return_value={"client_id": "cid"}
        )
        mocker.patch(
            "katalogue_cli.cli.auth.keyring.get_password", return_value="stored-secret"
        )

        result = runner.invoke(cli, ["auth", "status"])

        assert result.exit_code == 0
        assert "cid" in result.output
        assert "(set in keychain)" in result.output
        assert "stored-secret" not in result.output

    def test_missing_client_secret_exits_1(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        mocker.patch(
            "katalogue_cli.cli.auth.load_config_file", return_value={"client_id": "cid"}
        )
        mocker.patch("katalogue_cli.cli.auth.keyring.get_password", return_value=None)

        result = runner.invoke(cli, ["auth", "status"])

        assert result.exit_code == 1
        assert "(not set)" in result.output

    def test_missing_client_id_exits_1(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        mocker.patch("katalogue_cli.cli.auth.load_config_file", return_value={})
        mocker.patch("katalogue_cli.cli.auth.keyring.get_password", return_value=None)

        result = runner.invoke(cli, ["auth", "status"])

        assert result.exit_code == 1

    def test_shows_config_file_source_label(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        mocker.patch(
            "katalogue_cli.cli.auth.load_config_file", return_value={"client_id": "cid"}
        )
        mocker.patch("katalogue_cli.cli.auth.keyring.get_password", return_value="s")

        result = runner.invoke(cli, ["auth", "status"])

        assert "config file" in result.output

    def test_env_var_credential_shows_env_source(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "env-cid")
        mocker.patch("katalogue_cli.cli.auth.load_config_file", return_value={})
        mocker.patch("katalogue_cli.cli.auth.keyring.get_password", return_value="s")

        result = runner.invoke(cli, ["auth", "status"])

        assert result.exit_code == 0
        assert "env" in result.output.lower()

    def test_env_var_secret_shows_env_source(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "env-secret")
        mocker.patch(
            "katalogue_cli.cli.auth.load_config_file", return_value={"client_id": "cid"}
        )
        mock_keyring = mocker.patch("katalogue_cli.cli.auth.keyring.get_password")

        result = runner.invoke(cli, ["auth", "status"])

        assert result.exit_code == 0
        assert "environment" in result.output
        assert "env-secret" not in result.output
        mock_keyring.assert_not_called()

    def test_never_prints_secret_value(self, runner: CliRunner, mocker) -> None:
        mocker.patch(
            "katalogue_cli.cli.auth.load_config_file", return_value={"client_id": "cid"}
        )
        mocker.patch(
            "katalogue_cli.cli.auth.keyring.get_password",
            return_value="super-secret-value",
        )

        result = runner.invoke(cli, ["auth", "status"])

        assert "super-secret-value" not in result.output


class TestAuthLogout:
    def test_clears_token_cache_and_keychain(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        mocker.patch(
            "katalogue_cli.cli.auth.load_config_file", return_value={"client_id": "cid"}
        )
        mock_cache_cls = mocker.patch("katalogue_cli.cli.auth.DiskTokenCache")
        mock_delete = mocker.patch("katalogue_cli.cli.auth.keyring.delete_password")
        mocker.patch("katalogue_cli.cli.auth.clear_client_id")

        result = runner.invoke(cli, ["auth", "logout"])

        assert result.exit_code == 0
        mock_cache_cls.return_value.clear.assert_called_once()
        mock_delete.assert_called_once_with("katalogue", "cid")

    def test_prints_confirmation(self, runner: CliRunner, mocker) -> None:
        mocker.patch(
            "katalogue_cli.cli.auth.load_config_file", return_value={"client_id": "cid"}
        )
        mocker.patch("katalogue_cli.cli.auth.DiskTokenCache")
        mocker.patch("katalogue_cli.cli.auth.keyring.delete_password")
        mocker.patch("katalogue_cli.cli.auth.clear_client_id")

        result = runner.invoke(cli, ["auth", "logout"])

        assert result.output.strip() != ""

    def test_clears_client_id_from_config_file(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        mocker.patch(
            "katalogue_cli.cli.auth.load_config_file", return_value={"client_id": "cid"}
        )
        mock_clear = mocker.patch("katalogue_cli.cli.auth.clear_client_id")
        mocker.patch("katalogue_cli.cli.auth.DiskTokenCache")
        mocker.patch("katalogue_cli.cli.auth.keyring.delete_password")

        runner.invoke(cli, ["auth", "logout"])

        mock_clear.assert_called_once()

    def test_does_not_delete_config_file(self, runner: CliRunner, mocker) -> None:
        mock_write = mocker.patch("katalogue_cli.cli.auth.write_config_file")
        mocker.patch(
            "katalogue_cli.cli.auth.load_config_file", return_value={"client_id": "cid"}
        )
        mocker.patch("katalogue_cli.cli.auth.clear_client_id")
        mocker.patch("katalogue_cli.cli.auth.DiskTokenCache")
        mocker.patch("katalogue_cli.cli.auth.keyring.delete_password")

        runner.invoke(cli, ["auth", "logout"])

        mock_write.assert_not_called()

    def test_no_keychain_entry_still_exits_0(
        self, runner: CliRunner, mocker, monkeypatch
    ) -> None:
        import keyring.errors

        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        mocker.patch(
            "katalogue_cli.cli.auth.load_config_file", return_value={"client_id": "cid"}
        )
        mocker.patch("katalogue_cli.cli.auth.DiskTokenCache")
        mocker.patch(
            "katalogue_cli.cli.auth.keyring.delete_password",
            side_effect=keyring.errors.PasswordDeleteError("katalogue"),
        )
        mocker.patch("katalogue_cli.cli.auth.clear_client_id")

        result = runner.invoke(cli, ["auth", "logout"])

        assert result.exit_code == 0

    def test_no_client_id_exits_1(self, runner: CliRunner, mocker, monkeypatch) -> None:
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        mocker.patch("katalogue_cli.cli.auth.load_config_file", return_value={})
        mocker.patch("katalogue_cli.cli.auth.DiskTokenCache")

        result = runner.invoke(cli, ["auth", "logout"])

        assert result.exit_code == 1
