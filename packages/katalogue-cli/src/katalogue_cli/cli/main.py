"""Root CLI group and global options for katalogue."""

from __future__ import annotations

import logging

import click
from dotenv import load_dotenv

from katalogue_cli.cli.auth import auth
from katalogue_cli.cli.dataset import dataset
from katalogue_cli.cli.dataset_group import dataset_group
from katalogue_cli.cli.datasource import datasource
from katalogue_cli.cli.export import export
from katalogue_cli.cli.field import field
from katalogue_cli.cli.glossary import glossary
from katalogue_cli.cli.system import system
from katalogue_sdk import DEFAULT_BASE_URL, DEFAULT_TOKEN_URL

load_dotenv()


@click.group()
@click.version_option("0.1.0", prog_name="katalogue")
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
    help="OAuth2 client secret.",
)
@click.option(
    "--base-url",
    envvar="KATALOGUE_URL",
    default=DEFAULT_BASE_URL,
    show_envvar=True,
    help="API base URL.",
)
@click.option(
    "--token-url",
    envvar="KATALOGUE_TOKEN_URL",
    default=DEFAULT_TOKEN_URL,
    show_envvar=True,
    help="OAuth2 token URL.",
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
    base_url: str,
    token_url: str,
    verbose: bool,
) -> None:
    """Interact with the Katalogue Data Catalog API."""
    ctx.ensure_object(dict)
    ctx.obj["client_id"] = client_id
    ctx.obj["client_secret"] = client_secret
    ctx.obj["base_url"] = base_url
    ctx.obj["token_url"] = token_url
    ctx.obj["verbose"] = verbose
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG, format="%(name)s %(levelname)s %(message)s"
        )


cli.add_command(auth)
cli.add_command(system)
cli.add_command(datasource)
cli.add_command(dataset_group)
cli.add_command(dataset)
cli.add_command(field)
cli.add_command(glossary)
cli.add_command(export)
