"""Shared CLI helpers to reduce boilerplate across resource commands."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Callable

import click

from katalogue_sdk.client.api import KatalogueClient, AuthError, ApiError
from katalogue_sdk.config.settings import resolve_settings, ConfigError
from katalogue_cli.formatters.output import (
    format_compact_json,
    format_json,
    format_list_table,
    format_table,
)


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
            settings = resolve_settings(
                client_id=ctx.obj["client_id"],
                client_secret=ctx.obj["client_secret"],
                base_url=ctx.obj["base_url"],
                token_url=ctx.obj["token_url"],
            )
        except ConfigError as e:
            click.echo(f"Error: {e}", err=True)
            ctx.exit(1)
            return None
        ctx.obj["_client"] = KatalogueClient(settings)
    return ctx.obj["_client"]


def filter_fields(data: Any, fields: list[str] | None) -> Any:
    """Keep only the requested fields from a dict or list of dicts.

    Wrapped list responses (e.g. {"systems": [...]}) are unwrapped to a plain
    list when fields are requested - cleaner for scripting and AI agents.
    """
    if not fields:
        return data

    # Unwrap single-key wrapper dicts like {"systems": [...]}
    if isinstance(data, dict):
        values = list(data.values())
        if len(data) == 1 and isinstance(values[0], list):
            return filter_fields(values[0], fields)
        return {f: data[f] for f in fields if f in data}

    if isinstance(data, list):
        return [{f: row[f] for f in fields if f in row} for row in data]

    return data


def unwrap_list(data: Any) -> list[Any]:
    """Unwrap a single-key wrapper dict (e.g. {"fields": [...]}) to a plain list."""
    if isinstance(data, dict):
        values = list(data.values())
        if len(data) == 1 and isinstance(values[0], list):
            return values[0]
    return data if isinstance(data, list) else [data]


def filter_where(data: Any, key: str, value: Any) -> Any:
    """Keep only rows where data[key] == value. Unwraps wrapper dicts first."""
    rows = unwrap_list(data)
    return [row for row in rows if row.get(key) == value]


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

    data = filter_fields(data, fields)

    if fmt == "json":
        click.echo(format_json(data))
    elif fmt == "compact":
        click.echo(format_compact_json(data))
    elif isinstance(data, list):
        click.echo(format_list_table(data))
    else:
        click.echo(format_table(data))


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
