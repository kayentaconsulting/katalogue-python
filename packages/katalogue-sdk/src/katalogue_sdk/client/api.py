"""HTTP client for the Katalogue API using OAuth2 client credentials."""

from __future__ import annotations

import logging
from typing import Any, Final

from urllib.parse import quote

from oauthlib.oauth2 import BackendApplicationClient
from requests.exceptions import HTTPError
from requests_oauthlib import OAuth2Session

from katalogue_sdk.client.cache import InMemoryTokenCache, TokenCache, TokenEntry
from katalogue_sdk.config.settings import Settings, resolve_settings

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when the API returns 401 Unauthorized."""


class ApiError(Exception):
    """Raised when the API returns a non-success status code."""


class KatalogueClient:
    def __init__(
        self, settings: Settings | None = None, token_cache: TokenCache | None = None
    ) -> None:
        """Create a client.

        Args:
            settings: Explicit settings object. If omitted, credentials are
                resolved from environment variables (KATALOGUE_CLIENT_ID,
                KATALOGUE_CLIENT_SECRET) and URL defaults. Raises ConfigError
                if required credentials cannot be found.
            token_cache: Cache for OAuth2 access tokens. Defaults to an
                in-memory cache (no persistence across process restarts).
                Pass any TokenCache implementation for cross-invocation persistence.

        Examples:
            # From environment variables
            client = KatalogueClient()

            # Explicit settings
            from katalogue_sdk import resolve_settings
            client = KatalogueClient(resolve_settings(client_id="id", client_secret="secret"))
        """
        if settings is None:
            settings = resolve_settings()
        self._base_url: Final[str] = settings.base_url.rstrip("/")
        self._client_id: Final[str] = settings.client_id
        self._client_secret: Final = settings.client_secret
        self._token_url: Final[str] = settings.token_url
        self._client = BackendApplicationClient(client_id=settings.client_id)
        self._session: Final = OAuth2Session(client=self._client)
        self._current_scope: str | None = None
        self._cache: TokenCache = (
            token_cache if token_cache is not None else InMemoryTokenCache()
        )

    def _fetch_token(self, scope: str) -> None:
        logger.info("Fetching OAuth2 token with scope=%s", scope)
        self._client.scope = scope
        self._session.fetch_token(
            token_url=self._token_url,
            client_id=self._client_id,
            client_secret=quote(self._client_secret.get_secret_value()),
            scope=scope,
        )
        self._current_scope = scope
        key = f"{self._token_url}|{self._client_id}|{scope}"
        expires_at = self._session.token.get("expires_at", 0.0)
        access_token = self._session.token.get("access_token", "")
        self._cache.set(
            key,
            TokenEntry(access_token=access_token, expires_at=expires_at, scope=scope),
        )

    def _ensure_token(self, scope: str) -> None:
        key = f"{self._token_url}|{self._client_id}|{scope}"
        cached = self._cache.get(key)
        if cached is not None:
            logger.debug("Using cached token for scope=%s", scope)
            self._session.token = {
                "access_token": cached.access_token.get_secret_value(),
                "token_type": "Bearer",
                "expires_at": cached.expires_at,
            }
            self._current_scope = scope
            return
        self._fetch_token(scope)

    def _request(self, method: str, url: str, scope: str, **kwargs: Any) -> Any:
        self._ensure_token(scope)

        response = self._session.request(method, url, **kwargs)

        # Token expired - refresh and retry
        if response.status_code == 401:
            logger.info("Token expired, refreshing...")
            self._fetch_token(scope)
            response = self._session.request(method, url, **kwargs)

        return self._handle_response(response)

    def list_resource(self, resource: str) -> list[dict[str, Any]]:
        url = f"{self._base_url}/api/{resource}/all"
        return self._request("GET", url, scope=f"{resource}.read")

    def get_resource(self, resource: str, resource_id: str) -> dict[str, Any]:
        url = f"{self._base_url}/api/{resource}/{quote(str(resource_id), safe='')}"
        return self._request("GET", url, scope=f"{resource}.read")

    def list_by_parent(
        self, resource: str, parent_resource: str, parent_id: str
    ) -> list[dict[str, Any]]:
        url = f"{self._base_url}/api/{resource}/{parent_resource}/{quote(str(parent_id), safe='')}"
        return self._request("GET", url, scope=f"{resource}.read")

    def get_system_export(self, system_id: str) -> dict[str, Any]:
        url = f"{self._base_url}/api/export/system/{quote(str(system_id), safe='')}"
        return self._request("GET", url, scope="system.read")

    def get_glossary_export(self, glossary_id: str) -> dict[str, Any]:
        url = f"{self._base_url}/api/export/glossary/{quote(str(glossary_id), safe='')}"
        return self._request("GET", url, scope="glossary.read")

    def _handle_response(self, response: Any) -> Any:
        try:
            response.raise_for_status()
        except HTTPError:
            msg = self._extract_error_message(response)
            if response.status_code == 401:
                raise AuthError(msg) from None
            raise ApiError(msg) from None
        return response.json()

    @staticmethod
    def _extract_error_message(response: Any) -> str:
        try:
            body = response.json()
            return (
                body.get("message")
                or body.get("error")
                or f"API error (HTTP {response.status_code})"
            )
        except Exception:
            return f"API error (HTTP {response.status_code})"
