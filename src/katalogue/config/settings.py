"""Configuration resolution for katalogue-cli.

Precedence: explicit value (CLI flag) > environment variable > default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://demo-api.katalogue.se"
DEFAULT_TOKEN_URL = "https://demo-api.katalogue.se/oidc/token"


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    base_url: str
    token_url: str


def resolve_settings(
    client_id: str | None = None,
    client_secret: str | None = None,
    base_url: str | None = None,
    token_url: str | None = None,
) -> Settings:
    resolved_client_id = client_id or os.environ.get("KATALOGUE_CLIENT_ID")
    if not resolved_client_id:
        raise ConfigError(
            "No client ID provided. Set KATALOGUE_CLIENT_ID or pass --client-id."
        )

    resolved_client_secret = client_secret or os.environ.get("KATALOGUE_CLIENT_SECRET")
    if not resolved_client_secret:
        raise ConfigError(
            "No client secret provided. Set KATALOGUE_CLIENT_SECRET or pass --client-secret."
        )

    resolved_base_url = base_url or os.environ.get("KATALOGUE_URL") or DEFAULT_BASE_URL
    resolved_token_url = token_url or os.environ.get("KATALOGUE_TOKEN_URL") or DEFAULT_TOKEN_URL

    return Settings(
        client_id=resolved_client_id,
        client_secret=resolved_client_secret,
        base_url=resolved_base_url,
        token_url=resolved_token_url,
    )
