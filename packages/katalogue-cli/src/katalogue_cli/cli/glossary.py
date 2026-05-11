"""CLI commands for glossary resources."""

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
from katalogue_cli.formatters.defaults import DEFAULT_PROPERTIES


@click.group()
def glossary() -> None:
    """Manage glossary terms."""


@glossary.command("list")
@properties_option
@wide_option
@filter_option
@format_option("table")
@click.pass_context
def list_cmd(
    ctx: click.Context,
    properties: list[str] | None,
    wide: bool,
    filters: tuple[str, ...],
    fmt: str,
) -> None:
    """List all glossaries."""
    run_get(
        ctx,
        "glossary",
        lambda: build_list_options(
            filters=filters,
            properties=properties,
            fmt=fmt,
            default_properties=DEFAULT_PROPERTIES["glossary"],
            wide=wide,
        ),
        fmt,
        wide=wide,
    )


@glossary.command()
@properties_option
@filter_option
@get_output_options()
@click.argument("glossary_id")
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
    glossary_id: str,
) -> None:
    """Fetch and display a glossary by ID."""
    out_fmt = resolve_template_format(ctx, fmt, template)
    run_get(
        ctx,
        "glossary",
        lambda: build_get_options(
            resource_id=glossary_id,
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


@glossary.command("export")
@properties_option
@filter_option
@export_output_options()
@click.argument("glossary_id")
@click.pass_context
def export(
    ctx: click.Context,
    properties: list[str] | None,
    filters: tuple[str, ...],
    fmt: str,
    template: str | None,
    datatype_converter: str | None,
    output_dir: str,
    output_file: str | None,
    split_by: str | None,
    filename_template: str | None,
    overwrite: bool,
    dry_run: bool,
    glossary_id: str,
) -> None:
    """Export a full glossary hierarchy to file.

    Writes glossary-{id}.json to the current directory by default.
    Use --split-by to create one file per child resource level.
    """
    out_fmt = resolve_template_format(ctx, fmt, template)
    run_get(
        ctx,
        "glossary",
        lambda: build_export_options(
            resource="glossary",
            resource_id=glossary_id,
            filters=filters,
            properties=properties,
            fmt=out_fmt,
            template=template,
            datatype_converter=datatype_converter,
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


@glossary.command("keys")
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
    show_keys(ctx, lambda c: c.list_resource("glossary"), fmt)
