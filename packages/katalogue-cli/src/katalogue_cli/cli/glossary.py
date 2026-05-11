"""CLI commands for glossary resources."""

from __future__ import annotations

import click

from katalogue import UpdateOptions, load_records
from katalogue_cli.cli.common import (
    _resolve_str_flag,
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
    run_update,
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


@glossary.command("update")
@click.argument("glossary_id", required=False, type=int)
@click.option("--name", default=None, help="Glossary name.")
@click.option("--description", default=None, help="Glossary description.")
@click.option(
    "--from-file",
    default=None,
    metavar="FILE",
    help="YAML, JSON, or CSV file with records to update. Mutually exclusive with ID.",
)
@click.option(
    "--continue-on-error",
    is_flag=True,
    default=False,
    help="Update each record individually; continue past failures and report all results.",
)
@click.pass_context
def update(
    ctx: click.Context,
    glossary_id: int | None,
    name: str | None,
    description: str | None,
    from_file: str | None,
    continue_on_error: bool,
) -> None:
    """Update one or more glossaries.

    Provide a glossary ID and flags for single-record updates,
    or --from-file for batch updates.
    """
    if glossary_id is not None and from_file:
        raise click.UsageError("ID and --from-file are mutually exclusive.")
    if glossary_id is None and not from_file:
        raise click.UsageError("Provide a glossary ID or --from-file.")

    def _options() -> UpdateOptions:
        if from_file:
            return UpdateOptions(
                records=load_records(from_file), continue_on_error=continue_on_error
            )
        changes: dict = {}
        for param, key, raw in [
            ("name", "glossary_name", name),
            ("description", "glossary_description", description),
        ]:
            given, val = _resolve_str_flag(ctx, param, raw)
            if given:
                changes[key] = val
        return UpdateOptions(
            resource_id=glossary_id,
            changes=changes,
            continue_on_error=continue_on_error,
        )

    run_update(ctx, "glossary", _options)


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
