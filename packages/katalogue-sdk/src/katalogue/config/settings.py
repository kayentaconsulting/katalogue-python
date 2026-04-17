"""Configuration resolution for katalogue-sdk.

Precedence: explicit value (CLI flag) > environment variable > default.
"""

from __future__ import annotations

import os
import re

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError, field_validator

_URL_PATTERN = re.compile(r"^https?://\S+$")


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    client_id: str
    client_secret: SecretStr
    base_url: str
    token_url: str

    @field_validator("base_url", "token_url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not _URL_PATTERN.match(v):
            raise ValueError(
                f"Invalid URL: {v!r} — must start with http:// or https://"
            )
        return v


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

    resolved_base_url = base_url or os.environ.get("KATALOGUE_URL")
    if not resolved_base_url:
        raise ConfigError("No base URL provided. Set KATALOGUE_URL or pass --base-url.")

    resolved_token_url = (
        token_url
        or os.environ.get("KATALOGUE_TOKEN_URL")
        or f"{resolved_base_url.rstrip('/')}/oidc/token"
    )

    try:
        return Settings(
            client_id=resolved_client_id,
            client_secret=SecretStr(resolved_client_secret),
            base_url=resolved_base_url,
            token_url=resolved_token_url,
        )
    except ValidationError as e:
        raise ConfigError(f"Invalid configuration: {e.errors()[0]['msg']}") from None
