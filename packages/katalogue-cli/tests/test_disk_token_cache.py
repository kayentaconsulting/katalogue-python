"""Unit tests for DiskTokenCache."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from pydantic import SecretStr

from katalogue_cli.auth import DiskTokenCache
from katalogue_sdk.client.cache import TokenEntry


def _entry(
    scope: str = "system.read",
    ttl: float = 3600,
    access_token: str = "tok-abc",
) -> TokenEntry:
    return TokenEntry(
        access_token=SecretStr(access_token), expires_at=time.time() + ttl, scope=scope
    )


def _expired_entry(scope: str = "system.read") -> TokenEntry:
    return TokenEntry(
        access_token=SecretStr("tok-old"), expires_at=time.time() - 1, scope=scope
    )


@pytest.fixture
def cache(tmp_path: Path) -> DiskTokenCache:
    return DiskTokenCache(cache_dir=tmp_path)


@pytest.fixture
def cache_file(tmp_path: Path) -> Path:
    return tmp_path / "tokens.json"


class TestDiskTokenCache:
    def test_get_returns_none_when_file_missing(self, cache: DiskTokenCache) -> None:
        assert cache.get("k") is None

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions only")
    def test_set_creates_file_with_correct_permissions(
        self, cache: DiskTokenCache, cache_file: Path
    ) -> None:
        cache.set("k", _entry())
        assert cache_file.exists()
        assert cache_file.stat().st_mode & 0o777 == 0o600

    def test_set_then_get_returns_matching_entry(self, cache: DiskTokenCache) -> None:
        entry = _entry(access_token="mytoken", scope="system.read")
        cache.set("k", entry)
        result = cache.get("k")
        assert result is not None
        assert result.access_token.get_secret_value() == "mytoken"
        assert result.scope == "system.read"

    def test_get_returns_none_for_expired_entry(self, cache: DiskTokenCache) -> None:
        cache.set("k", _expired_entry())
        assert cache.get("k") is None

    def test_get_returns_none_within_30s_buffer(self, cache: DiskTokenCache) -> None:
        # 20 seconds in the future — inside the 30s expiry buffer
        entry = TokenEntry(
            access_token=SecretStr("tok"),
            expires_at=time.time() + 20,
            scope="system.read",
        )
        cache.set("k", entry)
        assert cache.get("k") is None

    def test_get_returns_entry_outside_30s_buffer(self, cache: DiskTokenCache) -> None:
        # 60 seconds in the future — outside the 30s buffer
        entry = TokenEntry(
            access_token=SecretStr("tok"),
            expires_at=time.time() + 60,
            scope="system.read",
        )
        cache.set("k", entry)
        assert cache.get("k") is not None

    def test_clear_empties_all_entries(self, cache: DiskTokenCache) -> None:
        cache.set("k1", _entry(scope="system.read"))
        cache.set("k2", _entry(scope="datasource.read"))
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_clear_on_missing_file_does_not_raise(self, cache: DiskTokenCache) -> None:
        cache.clear()  # no exception

    def test_corrupt_json_returns_none_without_raising(
        self, cache: DiskTokenCache, cache_file: Path
    ) -> None:
        cache_file.write_text("NOT JSON", encoding="utf-8")
        assert cache.get("k") is None

    def test_missing_fields_in_json_returns_none(
        self, cache: DiskTokenCache, cache_file: Path
    ) -> None:
        cache_file.write_text(
            json.dumps({"k": {"access_token": "t"}}), encoding="utf-8"
        )
        assert cache.get("k") is None

    def test_atomic_write_uses_temp_file_same_dir(
        self,
        cache: DiskTokenCache,
        cache_file: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        recorded: list[str] = []
        original_replace = os.replace

        def recording_replace(src: str, dst: str) -> None:
            recorded.append(src)
            original_replace(src, dst)

        monkeypatch.setattr(os, "replace", recording_replace)
        cache.set("k", _entry())
        assert len(recorded) == 1
        tmp_file = Path(recorded[0])
        assert tmp_file.parent == tmp_path

    def test_multiple_keys_coexist_in_file(self, cache: DiskTokenCache) -> None:
        e1 = _entry(scope="system.read", access_token="tok-1")
        e2 = _entry(scope="datasource.read", access_token="tok-2")
        cache.set("k1", e1)
        cache.set("k2", e2)
        assert cache.get("k1").access_token.get_secret_value() == "tok-1"  # type: ignore[union-attr]
        assert cache.get("k2").access_token.get_secret_value() == "tok-2"  # type: ignore[union-attr]
