"""Root CLI group and global options for katalogue."""

from __future__ import annotations

import importlib.metadata

import click

from katalogue_cli.cli.auth import auth
from katalogue_cli.cli.business_term import business_term
from katalogue_cli.cli.field_description import field_description
from katalogue_cli.logging import configure_logging
from katalogue_cli.cli.dataset import dataset
from katalogue_cli.cli.dataset_group import dataset_group
from katalogue_cli.cli.datasource import datasource
from katalogue_cli.cli.field import field
from katalogue_cli.cli.glossary import glossary
from katalogue_cli.cli.system import system


@click.group()
@click.version_option(
    importlib.metadata.version("katalogue-cli"), prog_name="katalogue"
)
@click.option(
    "--client-id",
    envvar="KATALOGUE_CLIENT_ID",
    default=None,
    show_envvar=True,
    help="OAuth2 client ID.",
)
@click.option(
    "--client-secret",
    envvar="KATALOGUE_CLIENT_SECRET",
    default=None,
    show_envvar=True,
    help="OAuth2 client secret. Prefer KATALOGUE_CLIENT_SECRET env var — flags appear in shell history.",
)
@click.option(
    "--base-url",
    envvar="KATALOGUE_URL",
    default=None,
    show_envvar=True,
    help="API base URL. Required — set KATALOGUE_URL or pass --base-url.",
)
@click.option(
    "--token-url",
    envvar="KATALOGUE_TOKEN_URL",
    default=None,
    show_envvar=True,
    help="OAuth2 token URL. Defaults to <base-url>/oidc/token if not set.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show request details on stderr.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    client_id: str | None,
    client_secret: str | None,
    base_url: str | None,
    token_url: str | None,
    verbose: bool,
) -> None:
    """Interact with the Katalogue Data Catalog API."""
    ctx.ensure_object(dict)
    ctx.obj["client_id"] = client_id
    ctx.obj["client_secret"] = client_secret
    ctx.obj["base_url"] = base_url
    ctx.obj["token_url"] = token_url
    ctx.obj["verbose"] = verbose
    configure_logging(verbose)


cli.add_command(auth)
cli.add_command(business_term)
cli.add_command(field_description)
cli.add_command(system)
cli.add_command(datasource)
cli.add_command(dataset_group)
cli.add_command(dataset)
cli.add_command(field)
cli.add_command(glossary)
