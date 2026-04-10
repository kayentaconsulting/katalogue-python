"""katalogue auth commands: login, status, logout."""

from __future__ import annotations

import os

import click
import keyring

from katalogue_cli.auth import DiskTokenCache
from katalogue_cli.config.file import (
    clear_client_id,
    load_config_file,
    write_config_file,
)
from katalogue_sdk.client.api import ApiError, AuthError, KatalogueClient
from katalogue_sdk.config.settings import (
    DEFAULT_BASE_URL,
    DEFAULT_TOKEN_URL,
    ConfigError,
    resolve_settings,
)

_KEYRING_SERVICE = "katalogue"
_NULL_BACKENDS = {"Keyring", "NullKeyring"}


@click.group()
def auth() -> None:
    """Manage authentication credentials."""


@auth.command("login")
@click.option("--client-id", default=None, help="OAuth2 client ID.")
@click.option(
    "--client-secret",
    default=None,
    hide_input=True,
    help="OAuth2 client secret.",
)
@click.option(
    "--base-url", default=None, help=f"API base URL (default: {DEFAULT_BASE_URL})."
)
@click.option(
    "--token-url",
    default=None,
    help=f"OAuth2 token URL (default: {DEFAULT_TOKEN_URL}).",
)
def login(
    client_id: str | None,
    client_secret: str | None,
    base_url: str | None,
    token_url: str | None,
) -> None:
    """Authenticate and save credentials to the OS keychain and config file."""
    # 1. Detect keyring backend before anything else.
    backend = keyring.get_keyring()
    if type(backend).__name__ in _NULL_BACKENDS:
        click.echo(
            "Error: no keychain backend available. "
            "Set KATALOGUE_CLIENT_SECRET as an environment variable instead.",
            err=True,
        )
        raise SystemExit(1)

    # 2. Prompt for any values not supplied via flags.
    if client_id is None:
        client_id = click.prompt("Client ID")
    if client_secret is None:
        client_secret = click.prompt("Client Secret", hide_input=True)
    if base_url is None:
        base_url = click.prompt("Base URL", default=DEFAULT_BASE_URL)
    if token_url is None:
        token_url = click.prompt("Token URL", default=DEFAULT_TOKEN_URL)

    # 3. Validate credentials by fetching a token via a probe API call.
    try:
        settings = resolve_settings(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            token_url=token_url,
        )
        client = KatalogueClient(settings)
        client.list_resource("system")
    except AuthError as exc:
        click.echo(f"Authentication failed: {exc}", err=True)
        raise SystemExit(1)
    except ConfigError as exc:
        click.echo(f"Configuration error: {exc}", err=True)
        raise SystemExit(1)
    except ApiError:
        pass  # Valid credentials; API-level error is not an auth failure.

    # 4. Persist non-secret fields to config file, then store secret in keychain.
    write_config_file(client_id=client_id, base_url=base_url, token_url=token_url)
    keyring.set_password(_KEYRING_SERVICE, client_id, client_secret)

    click.echo("Logged in. Run `katalogue system list` to get started.")


@auth.command("status")
def status() -> None:
    """Show the current authentication configuration and its sources."""
    file_cfg = load_config_file()

    env_id = os.environ.get("KATALOGUE_CLIENT_ID")
    file_id = file_cfg.get("client_id")

    if env_id:
        client_id: str | None = env_id
        id_label = f"{env_id} (environment)"
    elif file_id:
        client_id = file_id
        id_label = f"{file_id} (config file)"
    else:
        client_id = None
        id_label = "(not set)"

    env_secret = os.environ.get("KATALOGUE_CLIENT_SECRET")
    if env_secret:
        secret_set = True
        secret_label = "(set in environment)"
    elif client_id and keyring.get_password(_KEYRING_SERVICE, client_id) is not None:
        secret_set = True
        secret_label = "(set in keychain)"
    else:
        secret_set = False
        secret_label = "(not set)"

    click.echo(f"client_id:     {id_label}")
    click.echo(f"client_secret: {secret_label}")

    if not client_id or not secret_set:
        raise SystemExit(1)


@auth.command("logout")
@click.pass_context
def logout(ctx: click.Context) -> None:
    """Clear cached tokens and remove credentials from the OS keychain."""
    file_cfg = load_config_file()
    client_id = (
        ctx.obj.get("client_id")
        or os.environ.get("KATALOGUE_CLIENT_ID")
        or file_cfg.get("client_id")
    )

    if not client_id:
        click.echo(
            "Error: could not determine client_id — run `katalogue auth status` to diagnose.",
            err=True,
        )
        ctx.exit(1)
        return

    DiskTokenCache().clear()
    try:
        keyring.delete_password(_KEYRING_SERVICE, client_id)
    except keyring.errors.PasswordDeleteError:
        pass
    clear_client_id()
    click.echo("Logged out. Token cache cleared and keychain entry removed.")
