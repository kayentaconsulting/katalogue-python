"""CLI commands for dataset resources."""

from __future__ import annotations

import click

from katalogue.cli.common import fields_option, where_option, get_client, handle_api_call, show_keys


@click.group()
def dataset() -> None:
    """Manage datasets."""


@dataset.command("list")
@fields_option
@where_option
@click.option("--dataset-group", "dataset_group_id", default=None, help="Filter by dataset group ID.")
@click.option("--format", "fmt", type=click.Choice(["json", "table", "compact"]), default="json", help="Output format.")
@click.pass_context
def list_cmd(ctx: click.Context, fields: list[str] | None, where: list[tuple], dataset_group_id: str | None, fmt: str) -> None:
    """List datasets. Optionally filter by dataset group."""
    client = get_client(ctx)
    if not client:
        return
    if dataset_group_id:
        handle_api_call(ctx, lambda: client.list_by_parent("dataset", "dataset_group", dataset_group_id), fmt, fields=fields, where=where)
    else:
        handle_api_call(ctx, lambda: client.list_resource("dataset"), fmt, fields=fields, where=where)


@dataset.command()
@fields_option
@click.argument("dataset_id")
@click.option("--format", "fmt", type=click.Choice(["json", "table", "compact"]), default="json", help="Output format.")
@click.pass_context
def get(ctx: click.Context, fields: list[str] | None, dataset_id: str, fmt: str) -> None:
    """Fetch and display a dataset by ID."""
    client = get_client(ctx)
    if not client:
        return
    handle_api_call(ctx, lambda: client.get_resource("dataset", dataset_id), fmt, fields=fields)


@dataset.command()
@fields_option
@click.argument("dataset_id")
@click.option("--format", "fmt", type=click.Choice(["json", "table", "compact"]), default="json", help="Output format.")
@click.pass_context
def children(ctx: click.Context, fields: list[str] | None, dataset_id: str, fmt: str) -> None:
    """List fields belonging to this dataset."""
    client = get_client(ctx)
    if not client:
        return
    handle_api_call(ctx, lambda: client.list_by_parent("field", "dataset", dataset_id), fmt, fields=fields)


@dataset.command("keys")
@click.option("--format", "fmt", type=click.Choice(["lines", "json"]), default="lines", help="Output format.")
@click.pass_context
def keys_cmd(ctx: click.Context, fmt: str) -> None:
    """List available field names for use with --where and --fields."""
    client = get_client(ctx)
    if not client:
        return
    show_keys(ctx, lambda: client.list_resource("dataset"), fmt)
