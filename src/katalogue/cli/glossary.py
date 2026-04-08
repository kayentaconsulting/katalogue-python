"""CLI commands for glossary resources."""

from __future__ import annotations

import click

from katalogue.cli.common import fields_option, where_option, get_client, handle_api_call, show_keys


@click.group()
def glossary() -> None:
    """Manage glossary terms."""


@glossary.command("list")
@fields_option
@where_option
@click.option("--format", "fmt", type=click.Choice(["json", "table", "compact"]), default="json", help="Output format.")
@click.pass_context
def list_cmd(ctx: click.Context, fields: list[str] | None, where: list[tuple], fmt: str) -> None:
    """List all glossaries."""
    client = get_client(ctx)
    if not client:
        return
    handle_api_call(ctx, lambda: client.list_resource("glossary"), fmt, fields=fields, where=where)


@glossary.command()
@fields_option
@click.argument("glossary_id")
@click.option("--format", "fmt", type=click.Choice(["json", "table", "compact"]), default="json", help="Output format.")
@click.pass_context
def get(ctx: click.Context, fields: list[str] | None, glossary_id: str, fmt: str) -> None:
    """Fetch and display a glossary by ID."""
    client = get_client(ctx)
    if not client:
        return
    handle_api_call(ctx, lambda: client.get_resource("glossary", glossary_id), fmt, fields=fields)


@glossary.command("keys")
@click.option("--format", "fmt", type=click.Choice(["lines", "json"]), default="lines", help="Output format.")
@click.pass_context
def keys_cmd(ctx: click.Context, fmt: str) -> None:
    """List available field names for use with --where and --fields."""
    client = get_client(ctx)
    if not client:
        return
    show_keys(ctx, lambda: client.list_resource("glossary"), fmt)
