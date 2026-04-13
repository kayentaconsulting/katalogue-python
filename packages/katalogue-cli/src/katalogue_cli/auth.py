"""CLI-layer auth utilities: disk-backed token cache."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import platformdirs

from katalogue_sdk.client.cache import TOKEN_EXPIRY_BUFFER_SECONDS, TokenEntry

logger = logging.getLogger(__name__)

_CACHE_FILENAME = "tokens.json"


class DiskTokenCache:
    """Disk-backed token cache stored in the OS user cache directory.

    Tokens are persisted across CLI invocations so that each command does not
    need to fetch a fresh access token from the auth server.

    The cache file is written atomically (temp file in the same directory, then
    os.replace) and with mode 0o600 on POSIX systems.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is not None:
            self._path = cache_dir / _CACHE_FILENAME
        else:
            self._path = (
                Path(platformdirs.user_cache_dir("katalogue")) / _CACHE_FILENAME
            )

    def get(self, key: str) -> TokenEntry | None:
        data = self._load()
        raw = data.get(key)
        if raw is None:
            return None
        try:
            entry = TokenEntry(**raw)
        except Exception:
            logger.debug("Malformed cache entry for key=%s, ignoring", key)
            return None
        if entry.expires_at - TOKEN_EXPIRY_BUFFER_SECONDS <= time.time():
            logger.debug("Cached token for key=%s is expired or within 30s buffer", key)
            return None
        return entry

    def set(self, key: str, entry: TokenEntry) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = self._load()
        data[key] = {
            "access_token": entry.access_token.get_secret_value(),
            "expires_at": entry.expires_at,
            "scope": entry.scope,
        }
        self._write(data)

    def delete(self, key: str) -> None:
        data = self._load()
        if key in data:
            del data[key]
            self._write(data)

    def clear(self) -> None:
        if self._path.exists():
            self._write({})

    def _load(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug(
                "Failed to read token cache at %s, treating as empty", self._path
            )
            return {}

    def _write(self, data: dict) -> None:
        tmp_path = self._path.parent / f".tokens.tmp.{os.getpid()}"
        try:
            tmp_path.write_text(json.dumps(data), encoding="utf-8")
            # On POSIX restrict to owner only. On Windows the user-profile
            # directory ACLs provide equivalent protection; chmod is a no-op.
            if os.name != "nt":
                os.chmod(tmp_path, 0o600)
            os.replace(str(tmp_path), str(self._path))
        except Exception as exc:
            tmp_path.unlink(missing_ok=True)
            logger.warning("Failed to write token cache at %s: %s", self._path, exc)
