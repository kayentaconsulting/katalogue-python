"""Unit tests for TokenEntry and InMemoryTokenCache."""

from __future__ import annotations

import time

from pydantic import SecretStr

from katalogue_sdk.client.cache import InMemoryTokenCache, TokenEntry


def _entry(
    scope: str = "system.read", ttl: float = 3600, access_token: str = "tok-abc"
) -> TokenEntry:
    return TokenEntry(
        access_token=SecretStr(access_token), expires_at=time.time() + ttl, scope=scope
    )


class TestTokenEntry:
    def test_access_token_is_secret_str(self) -> None:
        entry = _entry()
        assert isinstance(entry.access_token, SecretStr)
        assert entry.access_token.get_secret_value() == "tok-abc"

    def test_expires_at_is_float(self) -> None:
        entry = _entry()
        assert isinstance(entry.expires_at, float)

    def test_scope_round_trips(self) -> None:
        entry = _entry(scope="datasource.read")
        assert entry.scope == "datasource.read"


class TestInMemoryTokenCache:
    def test_get_returns_none_for_unknown_key(self) -> None:
        cache = InMemoryTokenCache()
        assert cache.get("missing") is None

    def test_set_then_get_returns_entry(self) -> None:
        cache = InMemoryTokenCache()
        entry = _entry()
        cache.set("k", entry)
        result = cache.get("k")
        assert result is not None
        assert result.scope == entry.scope

    def test_delete_removes_entry(self) -> None:
        cache = InMemoryTokenCache()
        cache.set("k", _entry())
        cache.delete("k")
        assert cache.get("k") is None

    def test_clear_removes_all_entries(self) -> None:
        cache = InMemoryTokenCache()
        cache.set("k1", _entry(scope="system.read"))
        cache.set("k2", _entry(scope="datasource.read"))
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_set_overwrites_existing_entry(self) -> None:
        cache = InMemoryTokenCache()
        cache.set("k", _entry(access_token="old"))
        cache.set("k", _entry(access_token="new"))
        result = cache.get("k")
        assert result is not None
        assert result.access_token.get_secret_value() == "new"

    def test_independent_keys_do_not_collide(self) -> None:
        cache = InMemoryTokenCache()
        e1 = _entry(scope="system.read", access_token="tok-1")
        e2 = _entry(scope="datasource.read", access_token="tok-2")
        cache.set("k1", e1)
        cache.set("k2", e2)
        assert cache.get("k1").access_token.get_secret_value() == "tok-1"  # type: ignore[union-attr]
        assert cache.get("k2").access_token.get_secret_value() == "tok-2"  # type: ignore[union-attr]
