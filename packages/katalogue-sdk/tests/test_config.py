"""Tests for config/settings - OAuth2 credential and URL resolution."""

import pytest

from katalogue.config.settings import resolve_settings, ConfigError


class TestClientIdResolution:
    def test_client_id_from_env_var(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "env-id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("KATALOGUE_URL", "https://test.katalogue.se")
        settings = resolve_settings()
        assert settings.client_id == "env-id"

    def test_client_id_from_explicit_value_overrides_env(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "env-id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("KATALOGUE_URL", "https://test.katalogue.se")
        settings = resolve_settings(client_id="explicit-id")
        assert settings.client_id == "explicit-id"

    def test_missing_client_id_raises_config_error(self, monkeypatch):
        monkeypatch.delenv("KATALOGUE_CLIENT_ID", raising=False)
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        with pytest.raises(ConfigError, match="client ID"):
            resolve_settings()


class TestClientSecretResolution:
    def test_client_secret_from_env_var(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "env-secret")
        monkeypatch.setenv("KATALOGUE_URL", "https://test.katalogue.se")
        settings = resolve_settings()
        assert settings.client_secret.get_secret_value() == "env-secret"

    def test_client_secret_from_explicit_value_overrides_env(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "env-secret")
        monkeypatch.setenv("KATALOGUE_URL", "https://test.katalogue.se")
        settings = resolve_settings(client_secret="explicit-secret")
        assert settings.client_secret.get_secret_value() == "explicit-secret"

    def test_missing_client_secret_raises_config_error(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.delenv("KATALOGUE_CLIENT_SECRET", raising=False)
        with pytest.raises(ConfigError, match="client secret"):
            resolve_settings()


class TestBaseUrlResolution:
    def test_base_url_from_env_var(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_URL", "https://custom.example.com")
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "secret")
        settings = resolve_settings()
        assert settings.base_url == "https://custom.example.com"

    def test_base_url_from_explicit_value_overrides_env(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_URL", "https://env.example.com")
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "secret")
        settings = resolve_settings(base_url="https://explicit.example.com")
        assert settings.base_url == "https://explicit.example.com"

    def test_base_url_required_when_not_set(self, monkeypatch):
        monkeypatch.delenv("KATALOGUE_URL", raising=False)
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "secret")
        with pytest.raises(ConfigError, match="KATALOGUE_URL"):
            resolve_settings()


class TestTokenUrlResolution:
    def test_token_url_from_env_var(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("KATALOGUE_URL", "https://test.katalogue.se")
        monkeypatch.setenv("KATALOGUE_TOKEN_URL", "https://auth.example.com/token")
        settings = resolve_settings()
        assert settings.token_url == "https://auth.example.com/token"

    def test_token_url_has_sensible_default(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("KATALOGUE_URL", "https://test.katalogue.se")
        monkeypatch.delenv("KATALOGUE_TOKEN_URL", raising=False)
        settings = resolve_settings()
        assert settings.token_url == "https://test.katalogue.se/oidc/token"


class TestSettingsSecurity:
    def test_repr_hides_secret(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "super-secret-value")
        monkeypatch.setenv("KATALOGUE_URL", "https://test.katalogue.se")
        settings = resolve_settings()
        assert "super-secret-value" not in repr(settings)
        assert "super-secret-value" not in str(settings)

    def test_invalid_base_url_raises_config_error(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "secret")
        with pytest.raises(ConfigError, match="[Uu]rl|URL"):
            resolve_settings(base_url="not-a-url")

    def test_invalid_token_url_raises_config_error(self, monkeypatch):
        monkeypatch.setenv("KATALOGUE_CLIENT_ID", "id")
        monkeypatch.setenv("KATALOGUE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("KATALOGUE_URL", "https://test.katalogue.se")
        with pytest.raises(ConfigError, match="[Uu]rl|URL"):
            resolve_settings(token_url="not-a-url")
