"""CLI commands for business term resources."""

from __future__ import annotations

import click

from katalogue import UpdateOptions, load_records
from katalogue_cli.cli.common import _resolve_str_flag, run_update


@click.group(name="business-term")
def business_term() -> None:
    """Manage business terms."""


@business_term.command("update")
@click.argument("term_id", required=False, type=int)
@click.option("--name", default=None, help="Business term name.")
@click.option("--description", default=None, help="Short description.")
@click.option("--definition", default=None, help="How values are determined.")
@click.option("--example", default=None, help="Illustrative example.")
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
    term_id: int | None,
    name: str | None,
    description: str | None,
    definition: str | None,
    example: str | None,
    from_file: str | None,
    continue_on_error: bool,
) -> None:
    """Update one or more business terms.

    Provide a term ID and flags for single-record updates, or --from-file for batch updates.
    """
    if term_id is not None and from_file:
        raise click.UsageError("ID and --from-file are mutually exclusive.")
    if term_id is None and not from_file:
        raise click.UsageError("Provide a term ID or --from-file.")

    def _options() -> UpdateOptions:
        if from_file:
            return UpdateOptions(
                records=load_records(from_file), continue_on_error=continue_on_error
            )
        changes: dict = {}
        for param, key, raw in [
            ("name", "business_term_name", name),
            ("description", "business_term_description", description),
            ("definition", "business_term_definition", definition),
            ("example", "business_term_example", example),
        ]:
            given, val = _resolve_str_flag(ctx, param, raw)
            if given:
                changes[key] = val
        return UpdateOptions(
            resource_id=term_id, changes=changes, continue_on_error=continue_on_error
        )

    run_update(ctx, "business_term", _options)
