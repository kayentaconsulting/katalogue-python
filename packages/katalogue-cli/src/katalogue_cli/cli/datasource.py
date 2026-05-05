"""CLI commands for datasource resources."""

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


@click.group()
def datasource() -> None:
    """Manage datasources."""


@datasource.command("list")
@properties_option
@wide_option
@filter_option
@click.option("--system", "system_id", default=None, help="Filter by system ID.")
@format_option("table")
@click.pass_context
def list_cmd(
    ctx: click.Context,
    properties: list[str] | None,
    wide: bool,
    filters: tuple[str, ...],
    system_id: str | None,
    fmt: str,
) -> None:
    """List datasources. Optionally filter by system."""
    group_by = PARENT_GROUP["datasource"]
    run_get(
        ctx,
        "datasource",
        lambda: build_list_options(
            filters=filters,
            properties=properties,
            fmt=fmt,
            parent_id=system_id,
            default_fields=DEFAULT_FIELDS["datasource"],
            wide=wide,
            group_by=group_by,
        ),
        fmt,
        group_by=group_by,
        wide=wide,
    )


@datasource.command()
@properties_option
@filter_option
@get_output_options()
@click.argument("datasource_id")
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
    datasource_id: str,
) -> None:
    """Fetch and display a datasource by ID."""
    out_fmt = resolve_template_format(ctx, fmt, template)
    run_get(
        ctx,
        "datasource",
        lambda: build_get_options(
            resource_id=datasource_id,
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


@datasource.command("export")
@properties_option
@filter_option
@export_output_options()
@click.argument("datasource_id")
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
    datasource_id: str,
) -> None:
    """Export a full datasource hierarchy to file.

    Writes datasource-{id}.json to the current directory by default.
    Use --split-by to create one file per child resource level.
    """
    out_fmt = resolve_template_format(ctx, fmt, template)
    run_get(
        ctx,
        "datasource",
        lambda: build_export_options(
            resource="datasource",
            resource_id=datasource_id,
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
    """List available field names for use with --filter and --properties."""
    show_keys(ctx, lambda c: c.list_resource("datasource"), fmt)
