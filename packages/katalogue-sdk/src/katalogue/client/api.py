"""HTTP client for the Katalogue API using OAuth2 client credentials."""

from __future__ import annotations

import logging
from typing import Any, Final

from urllib.parse import quote

from oauthlib.oauth2 import BackendApplicationClient
from pydantic import SecretStr
from requests.exceptions import HTTPError
from requests_oauthlib import OAuth2Session

from katalogue.client.cache import InMemoryTokenCache, TokenCache, TokenEntry
from katalogue.config.settings import Settings, resolve_settings
from katalogue.formatters import format_descriptions_to_plaintext, format_resultset
from katalogue.utils import filter_fields, filter_resultset, sort_resultset

logger = logging.getLogger(__name__)

# Maps each resource to its immediate parent resource type (used in list_by_parent URLs).
# Top-level resources (system, glossary) have no parent and are omitted.
_PARENT_RESOURCE: dict[str, str] = {
    "datasource": "system",
    "dataset_group": "datasource",
    "dataset": "dataset_group",
    "field": "dataset",
}

# Maps each resource to the field name that holds its parent's ID.
# Used for scoped single-record lookups when both resource_id and parent_id are given.
_PARENT_ID_FIELD: dict[str, str] = {
    "datasource": "system_id",
    "dataset_group": "datasource_id",
    "dataset": "dataset_group_id",
    "field": "dataset_id",
}

_VALID_RESOURCES: frozenset[str] = frozenset(
    {"system", "datasource", "dataset_group", "dataset", "field", "glossary"}
)
_VALID_FORMATS: frozenset[str] = frozenset({"json", "compact"})
_VALID_SORT_DIRECTIONS: frozenset[str] = frozenset({"asc", "desc"})


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
            from katalogue import resolve_settings
            client = KatalogueClient(resolve_settings(client_id="id", client_secret="secret"))
        """
        if settings is None:
            settings = resolve_settings()
        self._base_url: Final[str] = settings.base_url.rstrip("/")
        self._client_id: Final[str] = settings.client_id
        self._client_secret: Final[SecretStr] = settings.client_secret
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
            client_secret=self._client_secret.get_secret_value(),
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

    def get_resource(self, resource: str, resource_id: int | str) -> dict[str, Any]:
        url = f"{self._base_url}/api/{resource}/{quote(str(resource_id), safe='')}"
        return self._request("GET", url, scope=f"{resource}.read")

    def list_by_parent(
        self, resource: str, parent_resource: str, parent_id: int | str
    ) -> list[dict[str, Any]]:
        url = f"{self._base_url}/api/{resource}/{parent_resource}/{quote(str(parent_id), safe='')}"
        return self._request("GET", url, scope=f"{resource}.read")

    def get(
        self,
        resource: str,
        resource_id: int | None = None,
        parent_id: int | None = None,
        filter: dict[str, Any] | None = None,
        fields: list[str] | None = None,
        sort: list[dict[str, str]] | None = None,
        format: str | None = None,
        format_descriptions_as_text: bool = False,
    ) -> Any:
        """Fetch a resource and apply filtering, sorting, and formatting in one call.

        Routing:
          resource_id only        -> get_resource (single record)
          parent_id only          -> list_by_parent (all children of that parent)
          resource_id + parent_id -> get_resource, returned only if it belongs to parent
          neither                 -> list_resource (all records)

        For top-level resources with no parent (system, glossary), parent_id is always
        ignored — both when combined with resource_id and when used alone.

        Args:
            resource: Resource type — "system", "datasource", "dataset_group",
                      "dataset", "field", or "glossary".
            resource_id: ID of a single record to fetch.
            parent_id: ID of the parent to filter children by.
            filter: AND-logic key/value pairs to filter the result set.
                    e.g. {"is_pii": True, "system_name": "Kayenta"}
            fields: Column names to keep. All other fields are dropped.
            sort: Multi-column sort spec applied in order.
                  e.g. [{"field_name": "asc"}, {"field_id": "desc"}]
            format: "json" for pretty-printed string, "compact" for minified string,
                    None (default) to return a Python object.
            format_descriptions_as_text: When True, converts Draft.js rich-text JSON
                    in description fields to plain text strings.

        Returns:
            Filtered, sorted, and formatted result. Type depends on `format`:
            None -> dict or list, "json"/"compact" -> str.
        """
        resource = resource.lower()
        if resource not in _VALID_RESOURCES:
            raise ValueError(
                f"Invalid resource '{resource}'. Must be one of: {', '.join(sorted(_VALID_RESOURCES))}"
            )
        if format is not None:
            format = format.lower()
            if format not in _VALID_FORMATS:
                raise ValueError(
                    f"Invalid format '{format}'. Must be one of: {', '.join(sorted(_VALID_FORMATS))}"
                )
        if sort:
            for spec in sort:
                for col, direction in spec.items():
                    if direction.lower() not in _VALID_SORT_DIRECTIONS:
                        raise ValueError(
                            f"Invalid sort direction '{direction}' for column '{col}'. Must be 'asc' or 'desc'."
                        )
                    spec[col] = direction.lower()

        if resource_id is not None:
            data: Any = self.get_resource(resource, resource_id)
            if parent_id is not None:
                parent_field = _PARENT_ID_FIELD.get(resource)
                if parent_field and data.get(parent_field) != parent_id:
                    return None
        elif parent_id is not None:
            parent_resource = _PARENT_RESOURCE.get(resource)
            if parent_resource is not None:
                data = self.list_by_parent(resource, parent_resource, parent_id)
            else:
                data = self.list_resource(resource)
        else:
            data = self.list_resource(resource)

        if filter:
            for key, value in filter.items():
                data = filter_resultset(data, key, value)

        data = filter_fields(data, fields)
        data = (
            sort_resultset(data if isinstance(data, list) else [data], sort)
            if sort
            else data
        )
        if format_descriptions_as_text:
            data = format_descriptions_to_plaintext(data)

        return format_resultset(data, format)

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
