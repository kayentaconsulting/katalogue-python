"""CLI commands for datasource resources."""

from __future__ import annotations

import click

from katalogue_cli.cli.common import (
    fields_option,
    where_option,
    handle_api_call,
    show_keys,
)


@click.group()
def datasource() -> None:
    """Manage datasources."""


@datasource.command("list")
@fields_option
@where_option
@click.option("--system", "system_id", default=None, help="Filter by system ID.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table", "compact"]),
    default="json",
    help="Output format.",
)
@click.pass_context
def list_cmd(
    ctx: click.Context,
    fields: list[str] | None,
    where: list[tuple],
    system_id: str | None,
    fmt: str,
) -> None:
    """List datasources. Optionally filter by system."""
    if system_id:
        handle_api_call(
            ctx,
            lambda c: c.list_by_parent("datasource", "system", system_id),
            fmt,
            fields=fields,
            where=where,
        )
    else:
        handle_api_call(
            ctx,
            lambda c: c.list_resource("datasource"),
            fmt,
            fields=fields,
            where=where,
        )


@datasource.command()
@fields_option
@click.argument("datasource_id")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table", "compact"]),
    default="json",
    help="Output format.",
)
@click.pass_context
def get(
    ctx: click.Context, fields: list[str] | None, datasource_id: str, fmt: str
) -> None:
    """Fetch and display a datasource by ID."""
    handle_api_call(
        ctx, lambda c: c.get_resource("datasource", datasource_id), fmt, fields=fields
    )


@datasource.command("keys")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["lines", "json"]),
    default="lines",
    help="Output format.",
)
@click.pass_context
def keys_cmd(ctx: click.Context, fmt: str) -> None:
    """List available field names for use with --where and --fields."""
    show_keys(ctx, lambda c: c.list_resource("datasource"), fmt)
