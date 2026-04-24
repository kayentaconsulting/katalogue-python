"""Tests for KatalogueClient token cache integration."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from oauthlib.oauth2.rfc6749.errors import InvalidScopeError
from pydantic import SecretStr

from katalogue.client.api import AuthError
from katalogue.client.cache import InMemoryTokenCache, TokenEntry
from katalogue.config.settings import Settings

_BASE_URL = "https://test.katalogue.se"
_TOKEN_URL = "https://test.katalogue.se/oidc/token"


def _settings() -> Settings:
    return Settings(
        client_id="test-id",
        client_secret=SecretStr("test-secret"),
        base_url=_BASE_URL,
        token_url=_TOKEN_URL,
    )


def _valid_entry(scope: str = "system.read") -> TokenEntry:
    return TokenEntry(
        access_token=SecretStr("cached-token"),
        expires_at=time.time() + 3600,
        scope=scope,
    )


def _cache_key(scope: str = "system.read") -> str:
    return f"{_TOKEN_URL}|test-id|{scope}"


@pytest.fixture
def mock_session():
    with patch("katalogue.client.api.OAuth2Session") as MockSession:
        session = MagicMock()
        session.authorized = False
        session.token = {}

        def _fetch_side_effect(**kwargs):
            session.token = {
                "access_token": "fetched-token",
                "token_type": "Bearer",
                "expires_at": time.time() + 3600,
            }
            session.authorized = True

        session.fetch_token.side_effect = _fetch_side_effect
        MockSession.return_value = session
        yield session


@pytest.fixture
def cache():
    return InMemoryTokenCache()


@pytest.fixture
def client(mock_session, cache):
    from katalogue.client.api import KatalogueClient

    return KatalogueClient(_settings(), token_cache=cache)


class TestClientTokenCache:
    def test_cache_miss_triggers_fetch_token(self, client, mock_session, cache) -> None:
        assert cache.get(_cache_key()) is None
        client._ensure_token("system.read")
        mock_session.fetch_token.assert_called_once()

    def test_cache_miss_stores_entry_in_cache(
        self, client, mock_session, cache
    ) -> None:
        client._ensure_token("system.read")
        entry = cache.get(_cache_key())
        assert entry is not None
        assert entry.scope == "system.read"

    def test_cache_hit_skips_fetch_token(self, client, mock_session, cache) -> None:
        cache.set(_cache_key(), _valid_entry())
        client._ensure_token("system.read")
        mock_session.fetch_token.assert_not_called()

    def test_expired_entry_triggers_refetch(self, client, mock_session, cache) -> None:
        expired = TokenEntry(
            access_token=SecretStr("old-token"),
            expires_at=time.time() - 1,
            scope="system.read",
        )
        cache.set(_cache_key(), expired)
        client._ensure_token("system.read")
        mock_session.fetch_token.assert_called_once()

    def test_unrelated_scope_still_triggers_refetch(
        self, client, mock_session, cache
    ) -> None:
        # glossary.read is not an ancestor of system.read — must fetch
        cache.set(_cache_key("system.read"), _valid_entry("system.read"))
        client._ensure_token("glossary.read")
        mock_session.fetch_token.assert_called_once()

    def test_cache_key_includes_token_url_client_id_scope(
        self, client, mock_session, cache
    ) -> None:
        client._ensure_token("system.read")
        expected_key = _cache_key("system.read")
        assert cache.get(expected_key) is not None

    def test_no_cache_arg_defaults_to_in_memory_cache(self) -> None:
        with patch("katalogue.client.api.OAuth2Session"):
            from katalogue.client.api import KatalogueClient

            c = KatalogueClient(_settings())
            assert isinstance(c._cache, InMemoryTokenCache)


class TestAncestorCacheFallback:
    def test_ancestor_cache_hit_reuses_broader_scope(
        self, client, mock_session, cache
    ) -> None:
        # system.read is an ancestor of datasource.read — should reuse without fetching
        cache.set(_cache_key("system.read"), _valid_entry("system.read"))
        client._ensure_token("datasource.read")
        mock_session.fetch_token.assert_not_called()

    def test_ancestor_cache_hit_deep_hierarchy(
        self, client, mock_session, cache
    ) -> None:
        # system.read is root ancestor of field.read — should reuse without fetching
        cache.set(_cache_key("system.read"), _valid_entry("system.read"))
        client._ensure_token("field.read")
        mock_session.fetch_token.assert_not_called()

    def test_ancestor_cache_applies_token_to_session(
        self, client, mock_session, cache
    ) -> None:
        entry = _valid_entry("system.read")
        cache.set(_cache_key("system.read"), entry)
        client._ensure_token("datasource.read")
        assert (
            mock_session.token["access_token"] == entry.access_token.get_secret_value()
        )


class TestScopeEscalation:
    def test_escalation_succeeds_with_root_scope(
        self, client, mock_session, cache
    ) -> None:
        # No cache; system.read fetch succeeds — only one fetch needed
        client._ensure_token("datasource.read")
        mock_session.fetch_token.assert_called_once()
        assert mock_session.fetch_token.call_args[1]["scope"] == "system.read"

    def test_escalation_caches_under_root_scope(
        self, client, mock_session, cache
    ) -> None:
        client._ensure_token("datasource.read")
        assert cache.get(_cache_key("system.read")) is not None

    def test_escalation_falls_back_on_invalid_scope(
        self, client, mock_session, cache
    ) -> None:
        # system.read rejected; datasource.read succeeds
        def _fetch_side_effect(**kwargs):
            if kwargs.get("scope") == "system.read":
                raise InvalidScopeError()
            mock_session.token = {
                "access_token": "fetched-token",
                "token_type": "Bearer",
                "expires_at": time.time() + 3600,
            }

        mock_session.fetch_token.side_effect = _fetch_side_effect
        client._ensure_token("datasource.read")
        assert mock_session.fetch_token.call_count == 2
        scopes_tried = [c[1]["scope"] for c in mock_session.fetch_token.call_args_list]
        assert scopes_tried == ["system.read", "datasource.read"]

    def test_escalation_all_scopes_rejected_raises_auth_error(
        self, client, mock_session, cache
    ) -> None:
        mock_session.fetch_token.side_effect = InvalidScopeError()
        with pytest.raises(AuthError):
            client._ensure_token("datasource.read")

    def test_escalation_non_scope_error_propagates_immediately(
        self, client, mock_session, cache
    ) -> None:
        mock_session.fetch_token.side_effect = RuntimeError("network failure")
        with pytest.raises(RuntimeError, match="network failure"):
            client._ensure_token("datasource.read")
        mock_session.fetch_token.assert_called_once()

    def test_top_level_resource_no_escalation(
        self, client, mock_session, cache
    ) -> None:
        # system has no ancestors — exactly one fetch attempt
        client._ensure_token("system.read")
        mock_session.fetch_token.assert_called_once()
        assert mock_session.fetch_token.call_args[1]["scope"] == "system.read"

    def test_glossary_no_escalation(self, client, mock_session, cache) -> None:
        client._ensure_token("glossary.read")
        mock_session.fetch_token.assert_called_once()
        assert mock_session.fetch_token.call_args[1]["scope"] == "glossary.read"
