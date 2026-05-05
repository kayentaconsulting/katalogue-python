"""CLI commands for field resources."""

from __future__ import annotations

import click

from katalogue_cli.cli.common import (
    build_get_options,
    build_list_options,
    filter_option,
    format_option,
    get_output_options,
    properties_option,
    resolve_template_format,
    run_get,
    show_keys,
    wide_option,
)

from katalogue_cli.formatters.defaults import DEFAULT_PROPERTIES, PARENT_GROUP


@click.group()
def field() -> None:
    """Manage fields."""


@field.command("list")
@properties_option
@wide_option
@filter_option
@click.option("--dataset", "dataset_id", default=None, help="Filter by dataset ID.")
@format_option("table")
@click.pass_context
def list_cmd(
    ctx: click.Context,
    properties: list[str] | None,
    wide: bool,
    filters: tuple[str, ...],
    dataset_id: str | None,
    fmt: str,
) -> None:
    """List fields. Optionally filter by dataset or column value."""
    group_by = PARENT_GROUP["field"]
    run_get(
        ctx,
        "field",
        lambda: build_list_options(
            filters=filters,
            properties=properties,
            fmt=fmt,
            parent_id=dataset_id,
            default_properties=DEFAULT_PROPERTIES["field"],
            wide=wide,
            group_by=group_by,
        ),
        fmt,
        group_by=group_by,
        wide=wide,
    )


@field.command()
@properties_option
@filter_option
@get_output_options()
@click.argument("field_id")
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
    field_id: str,
) -> None:
    """Fetch and display a field by ID."""
    out_fmt = resolve_template_format(ctx, fmt, template)
    run_get(
        ctx,
        "field",
        lambda: build_get_options(
            resource_id=field_id,
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


@field.command("export")
@click.argument("field_id")
@click.pass_context
def export(ctx: click.Context, field_id: str) -> None:
    """Fields do not support export."""
    raise click.UsageError(
        "Fields do not support export. "
        "Use 'katalogue dataset export <id>' to export a dataset including all its fields."
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
    """List available field names for use with --filter and --properties."""
    show_keys(ctx, lambda c: c.list_resource("field"), fmt)
