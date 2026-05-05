"""CLI commands for dataset group resources."""

from __future__ import annotations

import click

from katalogue_cli.cli.common import (
    build_export_options,
    build_get_options,
    build_list_options,
    export_output_options,
    filter_option,
    format_option,
    get_output_options,
    properties_option,
    resolve_template_format,
    run_get,
    show_keys,
    wide_option,
)
from katalogue_cli.formatters.defaults import DEFAULT_FIELDS, PARENT_GROUP


@click.group("dataset-group")
def dataset_group() -> None:
    """Manage dataset groups."""


@dataset_group.command("list")
@properties_option
@wide_option
@filter_option
@click.option(
    "--datasource", "datasource_id", default=None, help="Filter by datasource ID."
)
@format_option("table")
@click.pass_context
def list_cmd(
    ctx: click.Context,
    properties: list[str] | None,
    wide: bool,
    filters: tuple[str, ...],
    datasource_id: str | None,
    fmt: str,
) -> None:
    """List dataset groups. Optionally filter by datasource."""
    group_by = PARENT_GROUP["dataset_group"]
    run_get(
        ctx,
        "dataset_group",
        lambda: build_list_options(
            filters=filters,
            properties=properties,
            fmt=fmt,
            parent_id=datasource_id,
            default_fields=DEFAULT_FIELDS["dataset_group"],
            wide=wide,
            group_by=group_by,
        ),
        fmt,
        group_by=group_by,
        wide=wide,
    )


@dataset_group.command()
@properties_option
@filter_option
@get_output_options()
@click.argument("dataset_group_id")
@click.pass_context
def get(
    ctx: click.Context,
    properties: list[str] | None,
    filters: tuple[str, ...],
    fmt: str,
    template: str | None,
    include_children: bool,
    split_by: str | None,
    filename_template: str | None,
    output_dir: str | None,
    output_file: str | None,
    overwrite: bool,
    dry_run: bool,
    dataset_group_id: str,
) -> None:
    """Fetch and display a dataset group by ID."""
    out_fmt = resolve_template_format(ctx, fmt, template)
    run_get(
        ctx,
        "dataset_group",
        lambda: build_get_options(
            resource_id=dataset_group_id,
            filters=filters,
            properties=properties,
            fmt=out_fmt,
            template=template,
            include_children=include_children,
            output_file=output_file,
            output_dir=output_dir,
            split_by=split_by,
            filename_template=filename_template,
            overwrite=overwrite,
            dry_run=dry_run,
        ),
        out_fmt,
        dry_run=dry_run,
    )


@dataset_group.command("export")
@properties_option
@filter_option
@export_output_options()
@click.argument("dataset_group_id")
@click.pass_context
def export(
    ctx: click.Context,
    properties: list[str] | None,
    filters: tuple[str, ...],
    fmt: str,
    template: str | None,
    output_dir: str,
    output_file: str | None,
    split_by: str | None,
    filename_template: str | None,
    overwrite: bool,
    dry_run: bool,
    dataset_group_id: str,
) -> None:
    """Export a full dataset group hierarchy to file.

    Writes dataset_group-{id}.json to the current directory by default.
    Use --split-by to create one file per child resource level.
    """
    out_fmt = resolve_template_format(ctx, fmt, template)
    run_get(
        ctx,
        "dataset_group",
        lambda: build_export_options(
            resource="dataset_group",
            resource_id=dataset_group_id,
            filters=filters,
            properties=properties,
            fmt=out_fmt,
            template=template,
            output_dir=output_dir,
            output_file=output_file,
            split_by=split_by,
            filename_template=filename_template,
            overwrite=overwrite,
            dry_run=dry_run,
        ),
        out_fmt,
        dry_run=dry_run,
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
    """List available field names for use with --filter and --properties."""
    show_keys(ctx, lambda c: c.list_resource("dataset_group"), fmt)
