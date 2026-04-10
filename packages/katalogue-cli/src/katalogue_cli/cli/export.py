"""CLI commands for export operations."""

from __future__ import annotations

import click

from katalogue_cli.cli.common import fields_option, handle_api_call


@click.group()
def export() -> None:
    """Export full resource trees."""


@export.command("system")
@fields_option
@click.argument("system_id")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table", "compact"]),
    default="json",
    help="Output format.",
)
@click.pass_context
def export_system(
    ctx: click.Context, fields: list[str] | None, system_id: str, fmt: str
) -> None:
    """Export a full system tree by system ID."""
    handle_api_call(ctx, lambda c: c.get_system_export(system_id), fmt, fields=fields)


@export.command("glossary")
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
def export_glossary(
    ctx: click.Context, fields: list[str] | None, glossary_id: str, fmt: str
) -> None:
    """Export glossary entries by glossary ID."""
    handle_api_call(
        ctx, lambda c: c.get_glossary_export(glossary_id), fmt, fields=fields
    )
