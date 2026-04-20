"""CLI commands for dataset resources."""

from __future__ import annotations

import click

from katalogue_cli.cli.common import (
    fields_option,
    wide_option,
    where_option,
    handle_api_call,
    show_keys,
)
from katalogue_cli.formatters.defaults import DEFAULT_FIELDS, PARENT_GROUP


@click.group()
def dataset() -> None:
    """Manage datasets."""


@dataset.command("list")
@fields_option
@wide_option
@where_option
@click.option(
    "--dataset-group",
    "dataset_group_id",
    default=None,
    help="Filter by dataset group ID.",
)
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
    dataset_group_id: str | None,
    fmt: str,
) -> None:
    """List datasets. Optionally filter by dataset group."""
    if dataset_group_id:
        handle_api_call(
            ctx,
            lambda c: c.list_by_parent("dataset", "dataset_group", dataset_group_id),
            fmt,
            fields=fields,
            where=where,
            default_fields=DEFAULT_FIELDS["dataset"],
            wide=wide,
            group_by=PARENT_GROUP["dataset"],
        )
    else:
        handle_api_call(
            ctx,
            lambda c: c.list_resource("dataset"),
            fmt,
            fields=fields,
            where=where,
            default_fields=DEFAULT_FIELDS["dataset"],
            wide=wide,
            group_by=PARENT_GROUP["dataset"],
        )


@dataset.command()
@fields_option
@click.argument("dataset_id")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table", "compact"]),
    default="json",
    help="Output format.",
)
@click.pass_context
def get(
    ctx: click.Context, fields: list[str] | None, dataset_id: str, fmt: str
) -> None:
    """Fetch and display a dataset by ID."""
    handle_api_call(
        ctx, lambda c: c.get_resource("dataset", dataset_id), fmt, fields=fields
    )


@dataset.command("keys")
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
    show_keys(ctx, lambda c: c.list_resource("dataset"), fmt)
