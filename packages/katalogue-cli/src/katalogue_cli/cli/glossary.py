"""CLI commands for glossary resources."""

from __future__ import annotations

import click

from katalogue_cli.cli.common import (
    fields_option,
    wide_option,
    where_option,
    handle_api_call,
    show_keys,
)
from katalogue_cli.formatters.defaults import DEFAULT_FIELDS


@click.group()
def glossary() -> None:
    """Manage glossary terms."""


@glossary.command("list")
@fields_option
@wide_option
@where_option
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table", "compact"]),
    default="table",
    help="Output format.",
)
@click.pass_context
def list_cmd(
    ctx: click.Context,
    fields: list[str] | None,
    wide: bool,
    where: list[tuple],
    fmt: str,
) -> None:
    """List all glossaries."""
    handle_api_call(
        ctx,
        lambda c: c.list_resource("glossary"),
        fmt,
        fields=fields,
        where=where,
        default_fields=DEFAULT_FIELDS["glossary"],
        wide=wide,
    )


@glossary.command()
@fields_option
@click.argument("glossary_id")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table", "compact"]),
    default="json",
    help="Output format.",
)
@click.pass_context
def get(
    ctx: click.Context, fields: list[str] | None, glossary_id: str, fmt: str
) -> None:
    """Fetch and display a glossary by ID."""
    handle_api_call(
        ctx, lambda c: c.get_resource("glossary", glossary_id), fmt, fields=fields
    )


@glossary.command("keys")
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
    show_keys(ctx, lambda c: c.list_resource("glossary"), fmt)
