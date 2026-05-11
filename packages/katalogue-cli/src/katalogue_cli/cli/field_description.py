"""CLI commands for field description resources."""

from __future__ import annotations

import click

from katalogue import UpdateOptions, load_records
from katalogue_cli.cli.common import _resolve_str_flag, run_update


@click.group(name="field-description")
def field_description() -> None:
    """Manage field descriptions."""


@field_description.command("update")
@click.argument("fd_id", required=False, type=int)
@click.option("--name", default=None, help="Field description name.")
@click.option("--description", default=None, help="Short description.")
@click.option("--definition", default=None, help="How values are determined.")
@click.option("--example", default=None, help="Illustrative example.")
@click.option(
    "--pii", "is_pii", flag_value=True, default=None, help="Mark field as PII."
)
@click.option("--no-pii", "is_pii", flag_value=False, help="Mark field as non-PII.")
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
    fd_id: int | None,
    name: str | None,
    description: str | None,
    definition: str | None,
    example: str | None,
    is_pii: bool | None,
    from_file: str | None,
    continue_on_error: bool,
) -> None:
    """Update one or more field descriptions.

    Provide a field description ID and flags for single-record updates,
    or --from-file for batch updates.
    """
    if fd_id is not None and from_file:
        raise click.UsageError("ID and --from-file are mutually exclusive.")
    if fd_id is None and not from_file:
        raise click.UsageError("Provide a field description ID or --from-file.")

    def _options() -> UpdateOptions:
        if from_file:
            return UpdateOptions(
                records=load_records(from_file), continue_on_error=continue_on_error
            )
        changes: dict = {}
        for param, key, raw in [
            ("name", "field_description_name", name),
            ("description", "field_description_description", description),
            ("definition", "field_description_definition", definition),
            ("example", "field_description_example", example),
        ]:
            given, val = _resolve_str_flag(ctx, param, raw)
            if given:
                changes[key] = val
        if is_pii is not None:
            changes["is_pii"] = is_pii
        return UpdateOptions(
            resource_id=fd_id, changes=changes, continue_on_error=continue_on_error
        )

    run_update(ctx, "field_description", _options)
