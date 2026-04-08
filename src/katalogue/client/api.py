"""HTTP client for the Katalogue API using OAuth2 client credentials."""

from __future__ import annotations

import logging
from typing import Any, Final
from urllib.parse import quote, urljoin

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when the API returns 401 Unauthorized."""


class ApiError(Exception):
    """Raised when the API returns a non-success status code."""


class KatalogueClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str,
        token_url: str,
    ) -> None:
        self._base_url: Final[str] = base_url.rstrip("/")
        self._client_id: Final[str] = client_id
        self._client_secret: Final[str] = client_secret
        self._token_url: Final[str] = token_url
        self._client = BackendApplicationClient(client_id=client_id)
        self._session: Final = OAuth2Session(client=self._client)
        self._current_scope: str | None = None

    def _fetch_token(self, scope: str) -> None:
        logger.info("Fetching OAuth2 token with scope=%s", scope)
        self._client.scope = scope
        self._session.fetch_token(
            token_url=self._token_url,
            client_id=self._client_id,
            client_secret=quote(self._client_secret),
            scope=scope,
        )
        self._current_scope = scope

    def _ensure_token(self, scope: str) -> None:
        if not self._session.authorized or self._current_scope != scope:
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
        url = f"{self._base_url}/api/{resource}/{resource_id}"
        return self._request("GET", url, scope=f"{resource}.read")

    def list_by_parent(self, resource: str, parent_resource: str, parent_id: str) -> list[dict[str, Any]]:
        url = f"{self._base_url}/api/{resource}/{parent_resource}/{parent_id}"
        return self._request("GET", url, scope=f"{resource}.read")

    def get_system_export(self, system_id: str) -> dict[str, Any]:
        url = f"{self._base_url}/api/export/system/{system_id}"
        return self._request("GET", url, scope="system.read")

    def get_glossary_export(self, glossary_id: str) -> dict[str, Any]:
        url = f"{self._base_url}/api/export/glossary/{glossary_id}"
        return self._request("GET", url, scope="glossary.read")

    def _handle_response(self, response: Any) -> Any:
        if response.status_code == 401:
            try:
                body = response.json()
                msg = body.get("message") or body.get("error") or "Unauthorized"
            except Exception:
                msg = "Unauthorized"
            raise AuthError(msg)

        if response.status_code >= 400:
            try:
                body = response.json()
                msg = body.get("error") or f"API error (HTTP {response.status_code})"
            except Exception:
                msg = f"API error (HTTP {response.status_code})"
            raise ApiError(msg)

        return response.json()
