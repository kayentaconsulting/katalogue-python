"""CLI commands for dataset group resources."""

from __future__ import annotations

import click

from katalogue_cli.cli.common import (
    fields_option,
    wide_option,
    where_option,
    handle_api_call,
    show_keys,
)
from katalogue_cli.cli.defaults import DEFAULT_FIELDS, PARENT_GROUP


@click.group("dataset-group")
def dataset_group() -> None:
    """Manage dataset groups."""


@dataset_group.command("list")
@fields_option
@wide_option
@where_option
@click.option(
    "--datasource", "datasource_id", default=None, help="Filter by datasource ID."
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
    datasource_id: str | None,
    fmt: str,
) -> None:
    """List dataset groups. Optionally filter by datasource."""
    if datasource_id:
        handle_api_call(
            ctx,
            lambda c: c.list_by_parent("dataset_group", "datasource", datasource_id),
            fmt,
            fields=fields,
            where=where,
            default_fields=DEFAULT_FIELDS["dataset_group"],
            wide=wide,
            group_by=PARENT_GROUP["dataset_group"],
        )
    else:
        handle_api_call(
            ctx,
            lambda c: c.list_resource("dataset_group"),
            fmt,
            fields=fields,
            where=where,
            default_fields=DEFAULT_FIELDS["dataset_group"],
            wide=wide,
            group_by=PARENT_GROUP["dataset_group"],
        )


@dataset_group.command()
@fields_option
@click.argument("dataset_group_id")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table", "compact"]),
    default="json",
    help="Output format.",
)
@click.pass_context
def get(
    ctx: click.Context, fields: list[str] | None, dataset_group_id: str, fmt: str
) -> None:
    """Fetch and display a dataset group by ID."""
    handle_api_call(
        ctx,
        lambda c: c.get_resource("dataset_group", dataset_group_id),
        fmt,
        fields=fields,
    )


@dataset_group.command("keys")
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
    show_keys(ctx, lambda c: c.list_resource("dataset_group"), fmt)
