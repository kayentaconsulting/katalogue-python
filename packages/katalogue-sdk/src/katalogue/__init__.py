from katalogue.client.api import ApiError, AuthError, KatalogueClient
from katalogue.client.cache import TokenCache, TokenEntry
from katalogue.config.settings import (
    ConfigError,
    Settings,
    resolve_settings,
)
from katalogue.filters import Filter
from katalogue.options import GetOptions, OutputOptions
from katalogue.results import CatalogResult, WrittenFile

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
    # Options / results
    "Filter",
    "GetOptions",
    "OutputOptions",
    "CatalogResult",
    "WrittenFile",
]
