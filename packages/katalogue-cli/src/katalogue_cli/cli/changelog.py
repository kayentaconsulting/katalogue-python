"""CLI command for changelog and audit history."""

from __future__ import annotations

import click

from katalogue_cli.cli.common import (
    _handle_sdk_call,
    _output_options,
    _resolve_properties,
    emit_result,
    filter_option,
    get_output_options,
    properties_option,
    resolve_template_format,
)
from katalogue_cli.formatters.defaults import DEFAULT_PROPERTIES


@click.command()
@click.argument("object_name")
@click.argument("object_id", type=int)
@click.option(
    "--from",
    "from_date",
    default=None,
    metavar="DATE",
    help="Include entries on or after this date (YYYY-MM-DD).",
)
@click.option(
    "--to",
    "to_date",
    default=None,
    metavar="DATE",
    help="Include entries on or before this date (YYYY-MM-DD).",
)
@properties_option
@filter_option
@get_output_options("table")
@click.pass_context
def changelog(
    ctx: click.Context,
    object_name: str,
    object_id: int,
    from_date: str | None,
    to_date: str | None,
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
) -> None:
    """Fetch changelog entries for an asset or job.

    OBJECT_NAME is the asset type (system, datasource, dataset, field, job, …).
    OBJECT_ID is the numeric ID of the asset or job.

    Use --include-children to also fetch changelog for all child assets in the
    hierarchy (may generate many API calls; rate limit: 150 req/10 s).
    """
    out_fmt = resolve_template_format(ctx, fmt, template)
    output = _output_options(
        out_fmt,
        template=template,
        output_file=output_file,
        output_dir=output_dir,
        split_by=split_by,
        filename_template=filename_template,
        overwrite=overwrite,
        dry_run=dry_run,
    )
    resolved_properties = _resolve_properties(
        properties,
        out_fmt or "table",
        default_properties=DEFAULT_PROPERTIES.get("changelog"),
    )
    result = _handle_sdk_call(
        ctx,
        lambda client: client.get_changelog(
            object_name,
            object_id,
            from_date=from_date,
            to_date=to_date,
            filters=list(filters) or None,
            properties=resolved_properties,
            include_children=include_children,
            output=output,
        ),
    )
    if result is None:
        return
    emit_result(ctx, result, out_fmt, dry_run=dry_run)
