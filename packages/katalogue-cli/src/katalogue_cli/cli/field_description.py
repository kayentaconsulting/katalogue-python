"""CLI commands for field description resources."""

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
from katalogue_cli.formatters.defaults import DEFAULT_PROPERTIES, PARENT_GROUP


@click.group()
def field_description() -> None:
    """Manage field descriptions."""


@field_description.command("list")
@properties_option
@wide_option
@filter_option
@click.option("--field", "field_id", default=None, help="Filter by field ID.")
@click.option(
    "--business-term",
    "business_term_id",
    default=None,
    help="Filter by business term ID (via reference table).",
)
@format_option("table")
@click.pass_context
def list_cmd(
    ctx: click.Context,
    properties: list[str] | None,
    wide: bool,
    filters: tuple[str, ...],
    field_id: str | None,
    business_term_id: str | None,
    fmt: str,
) -> None:
    """List field descriptions. Optionally filter by field or business term."""
    if business_term_id is not None:
        run_get(
            ctx,
            "field_description",
            lambda: build_list_options(
                filters=filters,
                properties=properties,
                fmt=fmt,
                reference_parent_resource="business_term",
                reference_parent_id=business_term_id,
                default_properties=DEFAULT_PROPERTIES["field_description"],
                wide=wide,
            ),
            fmt,
            wide=wide,
        )
    else:
        group_by = PARENT_GROUP["field_description"] if field_id else None
        run_get(
            ctx,
            "field_description",
            lambda: build_list_options(
                filters=filters,
                properties=properties,
                fmt=fmt,
                parent_id=field_id,
                default_properties=DEFAULT_PROPERTIES["field_description"],
                wide=wide,
                group_by=group_by,
            ),
            fmt,
            group_by=group_by,
            wide=wide,
        )


@field_description.command()
@properties_option
@filter_option
@get_output_options()
@click.argument("field_description_id")
@click.pass_context
def get(
    ctx: click.Context,
    properties: list[str] | None,
    filters: tuple[str, ...],
    fmt: str,
    template: str | None,
    datatype_converter: str | None,
    include_children: bool,
    split_by: str | None,
    filename_template: str | None,
    output_dir: str | None,
    output_file: str | None,
    overwrite: bool,
    dry_run: bool,
    field_description_id: str,
) -> None:
    """Fetch and display a field description by ID."""
    out_fmt = resolve_template_format(ctx, fmt, template)
    run_get(
        ctx,
        "field_description",
        lambda: build_get_options(
            resource_id=field_description_id,
            filters=filters,
            properties=properties,
            fmt=out_fmt,
            template=template,
            datatype_converter=datatype_converter,
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


@field_description.command("export")
@properties_option
@filter_option
@export_output_options(include_template=False)
@click.argument("field_description_id")
@click.pass_context
def export(
    ctx: click.Context,
    properties: list[str] | None,
    filters: tuple[str, ...],
    fmt: str,
    datatype_converter: str | None,
    output_dir: str,
    output_file: str | None,
    split_by: str | None,
    filename_template: str | None,
    overwrite: bool,
    dry_run: bool,
    field_description_id: str,
) -> None:
    """Export a field description with its linked business terms and fields.

    Writes field_description-{id}.json to the current directory by default.
    """
    run_get(
        ctx,
        "field_description",
        lambda: build_export_options(
            resource="field_description",
            resource_id=field_description_id,
            filters=filters,
            properties=properties,
            fmt=fmt,
            template=None,
            datatype_converter=datatype_converter,
            output_dir=output_dir,
            output_file=output_file,
            split_by=split_by,
            filename_template=filename_template,
            overwrite=overwrite,
            dry_run=dry_run,
        ),
        fmt,
        dry_run=dry_run,
    )


@field_description.command("keys")
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
    show_keys(ctx, lambda c: c.list_resource("field_description"), fmt)
