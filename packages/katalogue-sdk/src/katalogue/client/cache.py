"""Token cache protocol and in-memory implementation for katalogue-sdk."""

from __future__ import annotations

import time
from typing import Protocol

from pydantic import BaseModel, SecretStr

TOKEN_EXPIRY_BUFFER_SECONDS: int = 30
"""Seconds before actual expiry at which a cached token is considered stale."""


class TokenEntry(BaseModel):
    """A cached OAuth2 access token with expiry metadata."""

    access_token: SecretStr
    expires_at: float  # unix timestamp
    scope: str


class TokenCache(Protocol):
    """Protocol for token cache implementations.

    The SDK defines the shape; the CLI (or any consumer) provides the implementation.
    """

    def get(self, key: str) -> TokenEntry | None: ...

    def set(self, key: str, entry: TokenEntry) -> None: ...

    def delete(self, key: str) -> None: ...

    def clear(self) -> None: ...


class InMemoryTokenCache:
    """In-memory token cache. Default for SDK standalone use — no disk I/O."""

    def __init__(self) -> None:
        self._store: dict[str, TokenEntry] = {}

    def get(self, key: str) -> TokenEntry | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at - TOKEN_EXPIRY_BUFFER_SECONDS <= time.time():
            return None
        return entry

    def set(self, key: str, entry: TokenEntry) -> None:
        self._store[key] = entry

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()
