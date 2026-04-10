"""Tests for KatalogueClient token cache integration."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from katalogue_sdk.client.cache import InMemoryTokenCache, TokenEntry
from katalogue_sdk.config.settings import Settings, DEFAULT_TOKEN_URL, DEFAULT_BASE_URL


def _settings() -> Settings:
    return Settings(
        client_id="test-id",
        client_secret="test-secret",
        base_url=DEFAULT_BASE_URL,
        token_url=DEFAULT_TOKEN_URL,
    )


def _valid_entry(scope: str = "system.read") -> TokenEntry:
    return TokenEntry(
        access_token="cached-token",
        expires_at=time.time() + 3600,
        scope=scope,
    )


def _cache_key(scope: str = "system.read") -> str:
    return f"{DEFAULT_TOKEN_URL}|test-id|{scope}"


@pytest.fixture
def mock_session():
    with patch("katalogue_sdk.client.api.OAuth2Session") as MockSession:
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
    from katalogue_sdk.client.api import KatalogueClient

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
            access_token="old-token",
            expires_at=time.time() - 1,
            scope="system.read",
        )
        cache.set(_cache_key(), expired)
        client._ensure_token("system.read")
        mock_session.fetch_token.assert_called_once()

    def test_scope_change_triggers_refetch(self, client, mock_session, cache) -> None:
        cache.set(_cache_key("system.read"), _valid_entry("system.read"))
        client._ensure_token("datasource.read")
        mock_session.fetch_token.assert_called_once()

    def test_cache_key_includes_token_url_client_id_scope(
        self, client, mock_session, cache
    ) -> None:
        client._ensure_token("system.read")
        expected_key = _cache_key("system.read")
        assert cache.get(expected_key) is not None

    def test_no_cache_arg_defaults_to_in_memory_cache(self) -> None:
        with patch("katalogue_sdk.client.api.OAuth2Session"):
            from katalogue_sdk.client.api import KatalogueClient

            c = KatalogueClient(_settings())
            assert isinstance(c._cache, InMemoryTokenCache)
