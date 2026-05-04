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
from katalogue.filters import Filter, FilterParser, apply_filter
from katalogue.formatters import format_descriptions_to_plaintext
from katalogue.options import GetOptions
from katalogue.output import OutputPipeline
from katalogue.results import CatalogResult
from katalogue.utils import filter_fields, sort_resultset, unwrap_list

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
_VALID_SORT_DIRECTIONS: frozenset[str] = frozenset({"asc", "desc"})


class AuthError(Exception):
    """Raised when the API returns 401 Unauthorized."""


class ApiError(Exception):
    """Raised when the API returns a non-success status code."""


def _apply_filters_to_list(rows: list[Any], filters: list[Filter]) -> list[Any]:
    for f in filters:
        rows = [row for row in rows if apply_filter(row, f)]
    return rows


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
        options: GetOptions | None = None,
    ) -> CatalogResult:
        """Fetch a resource and apply filtering, sorting, and field selection.

        Routing (based on options):
          resource_id only        -> get_resource (single record)
          parent_id only          -> list_by_parent (all children of that parent)
          resource_id + parent_id -> get_resource, data=None if parent mismatch
          neither                 -> list_resource (all records)

        For top-level resources with no parent (system, glossary), parent_id is always
        ignored.

        Args:
            resource: Resource type — one of the valid Katalogue resources.
            options: Fetch and output options. Pass None to use all defaults.

        Returns:
            CatalogResult with data, raw, output=None (formatting in slice 5),
            and metadata["strategy"] indicating which route was used.
        """
        if options is None:
            options = GetOptions()

        resource = resource.lower()
        if resource not in _VALID_RESOURCES:
            raise ValueError(
                f"Invalid resource '{resource}'. Must be one of: {', '.join(sorted(_VALID_RESOURCES))}"
            )

        if options.include_children:
            return self._get_hierarchical(resource, options)

        if options.sort:
            for spec in options.sort:
                for col, direction in spec.items():
                    if direction.lower() not in _VALID_SORT_DIRECTIONS:
                        raise ValueError(
                            f"Invalid sort direction '{direction}' for column '{col}'. Must be 'asc' or 'desc'."
                        )
                    spec[col] = direction.lower()

        # Parse filters once before fetching so bad filter strings fail fast.
        parsed_filters = FilterParser().parse(options.filters)

        resource_id = options.resource_id
        parent_id = options.parent_id
        if resource_id is not None:
            raw: Any = self.get_resource(resource, resource_id)
            data: Any = raw
            if parent_id is not None:
                parent_field = _PARENT_ID_FIELD.get(resource)
                if parent_field and data.get(parent_field) != parent_id:
                    data = None
            strategy = "single"
        elif parent_id is not None:
            parent_resource = _PARENT_RESOURCE.get(resource)
            if parent_resource is not None:
                raw = self.list_by_parent(resource, parent_resource, parent_id)
            else:
                raw = self.list_resource(resource)
            data = unwrap_list(raw)
            strategy = "list_by_parent"
        else:
            raw = self.list_resource(resource)
            data = unwrap_list(raw)
            strategy = "list"
        # Apply post-fetch processing to list results only.
        if isinstance(data, list):
            if parsed_filters:
                data = _apply_filters_to_list(data, parsed_filters)
            data = filter_fields(data, options.fields)
            if options.sort:
                data = sort_resultset(data, options.sort)
            if options.format_descriptions_as_text:
                data = format_descriptions_to_plaintext(data)
        elif data is not None:
            # Single record: apply field selection and description formatting only.
            data = filter_fields(data, options.fields)
            if options.format_descriptions_as_text:
                data = format_descriptions_to_plaintext(data)

        output, output_file, output_files = OutputPipeline().process(
            data, options.output, root_resource=resource
        )

        return CatalogResult(
            data=data,
            raw=raw,
            output=output,
            output_file=output_file,
            output_files=output_files,
            metadata={"strategy": strategy},
        )

    def _get_hierarchical(self, resource: str, options: GetOptions) -> CatalogResult:
        """Dispatch to hierarchical assembly for include_children=True."""
        from katalogue.exporting import (
            apply_hierarchical_filters,
            assemble_dataset,
            assemble_dataset_group,
            assemble_datasource,
            assemble_glossary,
            assemble_system,
        )

        _HIERARCHICAL_RESOURCES = frozenset(
            {"system", "datasource", "dataset_group", "dataset", "glossary"}
        )
        if resource not in _HIERARCHICAL_RESOURCES:
            raise ValueError(
                f"Resource '{resource}' does not support hierarchical retrieval. "
                f"Valid resources: {', '.join(sorted(_HIERARCHICAL_RESOURCES))}"
            )
        if options.resource_id is None:
            raise ValueError("include_children=True requires resource_id to be set")

        resource_id = options.resource_id

        assemblers = {
            "system": assemble_system,
            "datasource": assemble_datasource,
            "dataset_group": assemble_dataset_group,
            "dataset": assemble_dataset,
            "glossary": assemble_glossary,
        }
        strategy = (
            "export_endpoint" if resource in ("system", "glossary") else "recursive"
        )

        data = assemblers[resource](self, resource_id)
        raw = data  # flat shape is both raw and processed before filtering

        parsed_filters = FilterParser().parse(options.filters)
        if parsed_filters:
            data = apply_hierarchical_filters(
                data, parsed_filters, root_resource=resource
            )

        if options.fields:
            from katalogue.exporting import _META_KEYS

            preserved = {k: data[k] for k in _META_KEYS if k in data}
            filtered = filter_fields(data, options.fields)
            if isinstance(filtered, dict):
                filtered.update(preserved)
                data = filtered

        output, output_file, output_files = OutputPipeline().process(
            data, options.output, root_resource=resource
        )

        return CatalogResult(
            data=data,
            raw=raw,
            output=output,
            output_file=output_file,
            output_files=output_files,
            metadata={"strategy": strategy},
        )

    def get_system_export(self, system_id: int | str) -> dict[str, Any]:
        url = f"{self._base_url}/api/export/system/{quote(str(system_id), safe='')}"
        return self._request("GET", url, scope="system.read")

    def get_glossary_export(self, glossary_id: int | str) -> dict[str, Any]:
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
