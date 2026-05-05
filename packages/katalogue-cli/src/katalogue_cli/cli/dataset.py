"""CLI commands for dataset resources."""

from __future__ import annotations

import click

from katalogue_cli.cli.common import (
    build_export_options,
    build_get_options,
    build_list_options,
    export_output_options,
    fields_option,
    filter_option,
    format_option,
    get_output_options,
    resolve_template_format,
    run_get,
    show_keys,
    wide_option,
)
from katalogue_cli.formatters.defaults import DEFAULT_FIELDS, PARENT_GROUP


@click.group()
def dataset() -> None:
    """Manage datasets."""


@dataset.command("list")
@fields_option
@wide_option
@filter_option
@click.option(
    "--dataset-group",
    "dataset_group_id",
    default=None,
    help="Filter by dataset group ID.",
)
@format_option("table")
@click.pass_context
def list_cmd(
    ctx: click.Context,
    fields: list[str] | None,
    wide: bool,
    filters: tuple[str, ...],
    dataset_group_id: str | None,
    fmt: str,
) -> None:
    """List datasets. Optionally filter by dataset group."""
    group_by = PARENT_GROUP["dataset"]
    run_get(
        ctx,
        "dataset",
        lambda: build_list_options(
            filters=filters,
            fields=fields,
            fmt=fmt,
            parent_id=dataset_group_id,
            default_fields=DEFAULT_FIELDS["dataset"],
            wide=wide,
            group_by=group_by,
        ),
        fmt,
        group_by=group_by,
        wide=wide,
    )


@dataset.command()
@fields_option
@filter_option
@get_output_options()
@click.argument("dataset_id")
@click.pass_context
def get(
    ctx: click.Context,
    fields: list[str] | None,
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
    dataset_id: str,
) -> None:
    """Fetch and display a dataset by ID."""
    out_fmt = resolve_template_format(ctx, fmt, template)
    run_get(
        ctx,
        "dataset",
        lambda: build_get_options(
            resource_id=dataset_id,
            filters=filters,
            fields=fields,
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


@dataset.command("export")
@fields_option
@filter_option
@export_output_options()
@click.argument("dataset_id")
@click.pass_context
def export(
    ctx: click.Context,
    fields: list[str] | None,
    filters: tuple[str, ...],
    fmt: str,
    template: str | None,
    output_dir: str,
    output_file: str | None,
    split_by: str | None,
    filename_template: str | None,
    overwrite: bool,
    dry_run: bool,
    dataset_id: str,
) -> None:
    """Export a full dataset hierarchy to file.

    Writes dataset-{id}.json to the current directory by default.
    Use --split-by to create one file per child resource level.
    """
    out_fmt = resolve_template_format(ctx, fmt, template)
    run_get(
        ctx,
        "dataset",
        lambda: build_export_options(
            resource="dataset",
            resource_id=dataset_id,
            filters=filters,
            fields=fields,
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
    """List available field names for use with --filter and --fields."""
    show_keys(ctx, lambda c: c.list_resource("dataset"), fmt)
