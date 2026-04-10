"""CLI commands for field resources."""

from __future__ import annotations

import click

from katalogue_cli.cli.common import (
    fields_option,
    where_option,
    handle_api_call,
    show_keys,
)


@click.group()
def field() -> None:
    """Manage fields."""


@field.command("list")
@fields_option
@where_option
@click.option("--dataset", "dataset_id", default=None, help="Filter by dataset ID.")
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
    dataset_id: str | None,
    fmt: str,
) -> None:
    """List fields. Optionally filter by dataset or column value."""
    if dataset_id:
        handle_api_call(
            ctx,
            lambda c: c.list_by_parent("field", "dataset", dataset_id),
            fmt,
            fields=fields,
            where=where,
        )
    else:
        handle_api_call(
            ctx, lambda c: c.list_resource("field"), fmt, fields=fields, where=where
        )


@field.command()
@fields_option
@click.argument("field_id")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table", "compact"]),
    default="json",
    help="Output format.",
)
@click.pass_context
def get(ctx: click.Context, fields: list[str] | None, field_id: str, fmt: str) -> None:
    """Fetch and display a field by ID."""
    handle_api_call(
        ctx, lambda c: c.get_resource("field", field_id), fmt, fields=fields
    )


@field.command("keys")
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
    show_keys(ctx, lambda c: c.list_resource("field"), fmt)
