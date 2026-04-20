from katalogue.client.api import ApiError, AuthError, KatalogueClient
from katalogue.client.cache import TokenCache, TokenEntry
from katalogue.config.settings import (
    ConfigError,
    Settings,
    resolve_settings,
)
from katalogue.formatters import (
    format_compact_json,
    format_descriptions_to_plaintext,
    format_json,
    format_resultset,
)
from katalogue.utils import filter_fields, filter_resultset, sort_resultset

__all__ = [
    # Client
    "KatalogueClient",
    # Config / errors
    "Settings",
    "resolve_settings",
    "ConfigError",
    "AuthError",
    "ApiError",
    # Token cache (protocol + entry — needed to implement custom backends)
    "TokenCache",
    "TokenEntry",
    # Result set utilities
    "filter_fields",
    "filter_resultset",
    "sort_resultset",
    # Formatters
    "format_json",
    "format_compact_json",
    "format_descriptions_to_plaintext",
    "format_resultset",
]
