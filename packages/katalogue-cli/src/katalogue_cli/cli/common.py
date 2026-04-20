"""Shared CLI helpers to reduce boilerplate across resource commands."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Callable

import click
import keyring

from katalogue_cli.auth import DiskTokenCache
from katalogue_cli.config.file import load_config_file
from katalogue.client.api import KatalogueClient, AuthError, ApiError
from katalogue.config.settings import (
    resolve_settings,
    ConfigError,
)
from katalogue.utils import filter_fields, filter_where, unwrap_list
from katalogue_cli.formatters.output import format_json, format_output

_NULL_BACKENDS = {"Keyring", "NullKeyring"}


def _get_or_create_client(ctx: click.Context) -> KatalogueClient | None:
    """Return the cached client for this invocation, creating it on first call.

    Credential precedence (highest to lowest):
      1. CLI flags (--client-id, --client-secret) — stored in ctx.obj by main.py
      2. Environment variables read by Click (envvar= on each option) — also in ctx.obj
      3. Environment variables read by resolve_settings() as a fallback
      4. Hardcoded defaults (base_url, token_url only — credentials have no default)

    Note: KATALOGUE_CLIENT_ID and KATALOGUE_CLIENT_SECRET are read by both Click
    (via envvar=) and resolve_settings() (via os.environ). In practice Click wins
    because its value is passed explicitly; resolve_settings() only sees None when
    no flag or envvar was set.
    """
    if "_client" not in ctx.obj:
        try:
            file_cfg = load_config_file()
            client_id = ctx.obj["client_id"] or file_cfg.get("client_id")
            client_secret = ctx.obj["client_secret"]
            if not client_secret and client_id:
                client_secret = keyring.get_password("katalogue", client_id)
                if client_secret is None:
                    backend_name = type(keyring.get_keyring()).__name__
                    if backend_name in _NULL_BACKENDS:
                        click.echo(
                            "Error: No keyring backend is available on this system. "
                            "Run 'katalogue auth login' or set KATALOGUE_CLIENT_SECRET.",
                            err=True,
                        )
                    else:
                        click.echo(
                            "Error: No stored credentials found in keyring. "
                            "Run 'katalogue auth login' or set KATALOGUE_CLIENT_SECRET.",
                            err=True,
                        )
                    ctx.exit(1)
                    return None
            settings = resolve_settings(
                client_id=client_id,
                client_secret=client_secret,
                base_url=ctx.obj["base_url"] or file_cfg.get("base_url"),
                token_url=ctx.obj["token_url"] or file_cfg.get("token_url"),
            )
        except ConfigError as e:
            click.echo(f"Error: {e}", err=True)
            ctx.exit(1)
            return None
        ctx.obj["_client"] = KatalogueClient(settings, token_cache=DiskTokenCache())
    return ctx.obj["_client"]


def parse_where_value(value: str) -> bool | int | str:
    """Coerce a CLI string value to the most appropriate Python type.

    - "true"/"false" (case-insensitive) -> bool
    - pure integer strings -> int
    - everything else -> str unchanged
    """
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _parse_where_callback(
    ctx: click.Context,
    param: click.Parameter,
    values: tuple[str, ...],
) -> list[tuple[str, Any]]:
    """Parse a sequence of 'key=value' strings into typed (key, value) pairs."""
    result = []
    for item in values:
        if "=" not in item:
            raise click.BadParameter(
                f"Expected KEY=VALUE format, got: {item!r}",
                ctx=ctx,
                param=param,
            )
        key, _, raw = item.partition("=")
        result.append((key.strip(), parse_where_value(raw.strip())))
    return result


def handle_api_call(
    ctx: click.Context,
    call: Callable[[KatalogueClient], Any],
    fmt: str,
    fields: list[str] | None = None,
    where: Sequence[tuple[str, Any]] = (),
    default_fields: list[str] | None = None,
    wide: bool = False,
    group_by: list[tuple[str, str]] | None = None,
) -> None:
    """Execute an API call, handle errors, apply field filtering, and format output."""
    client = _get_or_create_client(ctx)
    if client is None:
        return
    data = _fetch_or_exit(ctx, lambda: call(client))
    if data is None:
        return

    for key, value in where:
        data = filter_where(data, key, value)

    effective_fields = fields or (None if wide or fmt != "table" else default_fields)

    # Always retain group_by fields so the grouped formatter can use them as headers
    if group_by and effective_fields:
        all_parent_fields = [f for id_f, name_f in group_by for f in (id_f, name_f)]
        extra = [f for f in all_parent_fields if f not in effective_fields]
        if extra:
            effective_fields = list(effective_fields) + extra

    data = filter_fields(data, effective_fields)

    click.echo(format_output(data, fmt, group_by=group_by, wide=wide))


def _fetch_or_exit(ctx: click.Context, call: Any) -> Any:
    """Execute call(), print errors and signal failure by returning None."""
    try:
        return call()
    except AuthError as e:
        click.echo(f"Authentication failed: {e}", err=True)
        ctx.exit(1)
        return None
    except ApiError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)
        return None


def show_keys(
    ctx: click.Context, call: Callable[[KatalogueClient], Any], fmt: str
) -> None:
    """Fetch the first record from a list call and print its sorted keys."""
    client = _get_or_create_client(ctx)
    if client is None:
        return
    data = _fetch_or_exit(ctx, lambda: call(client))
    if data is None:
        return

    rows = unwrap_list(data)
    keys = sorted(rows[0].keys()) if rows else []

    if fmt == "json":
        click.echo(format_json(keys))
    else:
        for key in keys:
            click.echo(key)


# Reusable --where decorator for list commands
where_option = click.option(
    "--where",
    "where",
    multiple=True,
    callback=_parse_where_callback,
    metavar="KEY=VALUE",
    help=(
        "Filter by KEY=VALUE. Repeatable for AND logic. "
        "Values are coerced: true/false -> bool, integers -> int."
    ),
)

# Reusable --fields decorator for all resource commands
fields_option = click.option(
    "--fields",
    default=None,
    help="Comma-separated field names to include in output.",
    callback=lambda ctx, param, v: v.split(",") if v else None,
    is_eager=False,
)

# Reusable --wide decorator for list commands
wide_option = click.option(
    "--wide",
    is_flag=True,
    default=False,
    help="Show all fields in table output (overrides default field selection).",
)
