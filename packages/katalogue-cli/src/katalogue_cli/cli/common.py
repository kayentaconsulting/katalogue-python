"""Shared CLI helpers to reduce boilerplate across resource commands."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

import click
import keyring
from pydantic import ValidationError

from katalogue import (
    ApiError,
    AuthError,
    CatalogResult,
    GetOptions,
    KatalogueClient,
    OutputOptions,
)
from katalogue.config.settings import ConfigError, resolve_settings
from katalogue.utils import filter_properties as filter_properties
from katalogue.utils import unwrap_list
from katalogue_cli.auth import DiskTokenCache
from katalogue_cli.config.file import load_config_file
from katalogue_cli.formatters.output import format_json, format_output

_NULL_BACKENDS = {"Keyring", "NullKeyring"}
_FORMAT_CHOICES = ["json", "yaml", "yml", "json-compact", "compact", "csv", "table"]
_EXPORT_FORMAT_CHOICES = ["json", "yaml", "yml", "json-compact", "compact", "csv"]
_FORMAT_HELP = "Serialization format for output."
_DATATYPE_CONVERTER_HELP = (
    "Datatype converter to apply. Built-in: sqlserver-to-databricks, db2-to-databricks. "
    "Repo-local names can be registered in katalogue.toml or [tool.katalogue.datatype_converters] "
    "inside pyproject.toml. Or provide a path to a .yaml or .yml file."
)
_TEMPLATE_HELP = (
    "Template to apply. Built-in: dbt-source, column-mapping, json-template. "
    "Repo-local names can be registered in katalogue.toml or [tool.katalogue.templates] "
    "inside pyproject.toml. "
    "Or provide a path to a .j2 file."
)

T = TypeVar("T")


def _get_or_create_client(ctx: click.Context) -> KatalogueClient | None:
    """Return the cached client for this invocation, creating it on first call."""
    if "_client" not in ctx.obj:
        try:
            file_cfg = load_config_file()
            client_id = ctx.obj["client_id"] or file_cfg.get("client_id")
            client_secret = ctx.obj["client_secret"]
            if not client_secret and client_id:
                client_secret = keyring.get_password("katalogue", client_id)
                if client_secret is None:
                    backend_name = type(keyring.get_keyring()).__name__
                    if backend_name in _NULL_BACKENDS:
                        click.echo(
                            "Error: No keyring backend is available on this system. "
                            "Run 'katalogue auth login' or set KATALOGUE_CLIENT_SECRET.",
                            err=True,
                        )
                    else:
                        click.echo(
                            "Error: No stored credentials found in keyring. "
                            "Run 'katalogue auth login' or set KATALOGUE_CLIENT_SECRET.",
                            err=True,
                        )
                    ctx.exit(1)
                    return None
            settings = resolve_settings(
                client_id=client_id,
                client_secret=client_secret,
                base_url=ctx.obj["base_url"] or file_cfg.get("base_url"),
                token_url=ctx.obj["token_url"] or file_cfg.get("token_url"),
            )
        except ConfigError as e:
            click.echo(f"Error: {e}", err=True)
            ctx.exit(1)
            return None
        ctx.obj["_client"] = KatalogueClient(settings, token_cache=DiskTokenCache())
    return ctx.obj["_client"]


def _handle_sdk_call(
    ctx: click.Context,
    call: Callable[[KatalogueClient], T],
) -> T | None:
    """Execute an SDK call and map SDK/user-input errors to CLI exits."""
    client = _get_or_create_client(ctx)
    if client is None:
        return None

    try:
        return call(client)
    except AuthError as e:
        click.echo(f"Authentication failed: {e}", err=True)
        ctx.exit(1)
        return None
    except ApiError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)
        return None
    except (ValidationError, ValueError, FileExistsError, FileNotFoundError) as e:
        raise click.UsageError(str(e)) from None


def emit_result(
    ctx: click.Context,
    result: CatalogResult,
    fmt: str | None,
    *,
    group_by: list[tuple[str, str]] | None = None,
    wide: bool = False,
    dry_run: bool = False,
) -> None:
    """Emit a CatalogResult using CLI presentation rules."""
    _ = ctx
    if result.output_files:
        verb = "Would write" if dry_run else "Wrote"
        click.echo(f"{verb} {len(result.output_files)} files")
        for written in result.output_files:
            click.echo(written.path)
        return

    if result.output_file:
        verb = "Would write" if dry_run else "Wrote"
        click.echo(f"{verb} {result.output_file}")
        return

    if result.output is not None:
        click.echo(result.output)
        return

    no_match_message = _summarize_empty_hierarchical_result(result)
    if no_match_message is not None:
        click.echo(no_match_message, err=True)
        return

    if fmt == "table":
        click.echo(format_output(result.data, "table", group_by=group_by, wide=wide))
        return

    click.echo(repr(result.data))


def _summarize_empty_hierarchical_result(result: CatalogResult) -> str | None:
    """Return a concise warning for split exports that filtered everything away."""
    data = result.data
    if not isinstance(data, dict):
        return None

    datasets = data.get("datasets")
    fields = data.get("fields")
    if not isinstance(datasets, list) or datasets:
        return None
    if fields is not None and not isinstance(fields, list):
        return None
    if fields is not None and fields:
        return None

    resource = data.get("resource")
    resource_id = data.get("id")
    if resource and resource_id is not None:
        return (
            f"No datasets matched the filter for {resource} {resource_id}. "
            "No files were written."
        )
    return "No datasets matched the filter. No files were written."


def _resolve_properties(
    properties: list[str] | None,
    fmt: str,
    *,
    default_properties: list[str] | None = None,
    wide: bool = False,
    group_by: list[tuple[str, str]] | None = None,
) -> list[str] | None:
    effective_properties = properties or (
        None if wide or fmt != "table" else default_properties
    )
    if group_by and effective_properties:
        all_parent_properties = [f for id_f, name_f in group_by for f in (id_f, name_f)]
        extra = [f for f in all_parent_properties if f not in effective_properties]
        if extra:
            effective_properties = list(effective_properties) + extra
    return effective_properties


def _output_options(
    fmt: str | None,
    *,
    template: str | None = None,
    output_file: str | None = None,
    output_dir: str | None = None,
    split_by: str | None = None,
    filename_template: str | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> OutputOptions:
    if fmt == "table" and template:
        raise ValueError(
            "table format cannot be combined with --template; "
            "omit --format or choose json, yaml, or csv."
        )
    if fmt == "table" and any(
        [output_file, output_dir, split_by, filename_template, overwrite, dry_run]
    ):
        raise ValueError(
            "table format cannot be combined with file output options; "
            "use json, yaml, csv, or a template"
        )
    return OutputOptions(
        format=None if fmt == "table" else fmt,
        template=template,
        output_file=output_file,
        output_dir=output_dir,
        split_by=split_by,
        filename_template=filename_template,
        overwrite=overwrite,
        dry_run=dry_run,
    )


def build_list_options(
    *,
    filters: tuple[str, ...],
    properties: list[str] | None,
    fmt: str,
    parent_id: str | None = None,
    default_properties: list[str] | None = None,
    wide: bool = False,
    group_by: list[tuple[str, str]] | None = None,
) -> GetOptions:
    return GetOptions(
        parent_id=parent_id,
        filters=list(filters) or None,
        properties=_resolve_properties(
            properties,
            fmt,
            default_properties=default_properties,
            wide=wide,
            group_by=group_by,
        ),
        output=_output_options(fmt),
    )


def build_get_options(
    *,
    resource_id: str,
    filters: tuple[str, ...],
    properties: list[str] | None,
    fmt: str | None,
    template: str | None = None,
    include_children: bool,
    output_file: str | None,
    output_dir: str | None,
    split_by: str | None,
    filename_template: str | None,
    overwrite: bool,
    dry_run: bool,
    datatype_converter: str | None = None,
) -> GetOptions:
    return GetOptions(
        resource_id=resource_id,
        filters=list(filters) or None,
        properties=properties,
        include_children=include_children,
        datatype_converter=datatype_converter,
        output=_output_options(
            fmt,
            template=template,
            output_file=output_file,
            output_dir=output_dir,
            split_by=split_by,
            filename_template=filename_template,
            overwrite=overwrite,
            dry_run=dry_run,
        ),
    )


def resolve_template_format(
    ctx: click.Context, fmt: str, template: str | None
) -> str | None:
    """Return None when --template is given but --format was not explicitly set.

    This lets the template render in its natural format (YAML for dbt-source,
    JSON for json-template) instead of being silently converted to the CLI default.
    """
    from click.core import ParameterSource

    if template and ctx.get_parameter_source("fmt") == ParameterSource.DEFAULT:
        return None
    return fmt


def run_get(
    ctx: click.Context,
    resource: str,
    options_factory: Callable[[], GetOptions],
    fmt: str | None,
    *,
    group_by: list[tuple[str, str]] | None = None,
    wide: bool = False,
    dry_run: bool = False,
) -> None:
    try:
        options = options_factory()
    except (ValidationError, ValueError, FileExistsError, FileNotFoundError) as e:
        raise click.UsageError(str(e)) from None

    result = _handle_sdk_call(ctx, lambda client: client.get(resource, options))
    if result is None:
        return
    emit_result(ctx, result, fmt, group_by=group_by, wide=wide, dry_run=dry_run)


def show_keys(
    ctx: click.Context, call: Callable[[KatalogueClient], object], fmt: str
) -> None:
    """Fetch the first record from a list call and print its sorted keys."""
    data = _handle_sdk_call(ctx, call)
    if data is None:
        return

    rows = unwrap_list(data)
    keys = sorted(rows[0].keys()) if rows else []

    if fmt == "json":
        click.echo(format_json(keys))
    else:
        for key in keys:
            click.echo(key)


filter_option = click.option(
    "--filter",
    "-w",
    "filters",
    multiple=True,
    metavar="FILTER",
    help=(
        'Filter expression such as is_pii=true or system.name="CRM". '
        "Repeat for AND logic."
    ),
)

properties_option = click.option(
    "--properties",
    "-p",
    default=None,
    help="Comma-separated property names to include in output.",
    callback=lambda ctx, param, v: v.split(",") if v else None,
    is_eager=False,
)

wide_option = click.option(
    "--wide",
    is_flag=True,
    default=False,
    help="Show all properties in table output (overrides default property selection).",
)


def format_option(default: str) -> Callable[[Any], Any]:
    return click.option(
        "--format",
        "-f",
        "fmt",
        default=default,
        show_default=True,
        type=click.Choice(_FORMAT_CHOICES, case_sensitive=False),
        help=_FORMAT_HELP,
    )


template_option = click.option(
    "--template",
    "-t",
    default=None,
    metavar="TEMPLATE",
    help=_TEMPLATE_HELP,
)

datatype_converter_option = click.option(
    "--datatype-converter",
    default=None,
    metavar="MAPPING",
    help=_DATATYPE_CONVERTER_HELP,
)


def _export_extension(fmt: str | None, template: str | None) -> str:
    if template and not fmt:
        from katalogue.rendering import get_template_extension

        return get_template_extension(template)
    if fmt in ("yaml", "yml"):
        return "yaml"
    if fmt == "csv":
        return "csv"
    return "json"


def export_format_option() -> Callable[[Any], Any]:
    return click.option(
        "--format",
        "-f",
        "fmt",
        default="json",
        show_default=True,
        type=click.Choice(_EXPORT_FORMAT_CHOICES, case_sensitive=False),
        help=_FORMAT_HELP,
    )


def export_output_options() -> Callable[[Any], Any]:
    def decorator(func: Any) -> Any:
        func = click.option(
            "--dry-run",
            is_flag=True,
            default=False,
            help="Show planned output files without writing them.",
        )(func)
        func = click.option(
            "--overwrite",
            is_flag=True,
            default=False,
            help="Overwrite existing output files.",
        )(func)
        func = click.option(
            "--filename-template",
            default=None,
            help="Jinja2 filename expression — only used with --split-by.",
        )(func)
        func = click.option(
            "--split-by",
            "-s",
            default=None,
            help="Split into one file per resource level. Files are written to --output-dir.",
        )(func)
        func = click.option(
            "--output-file",
            "-o",
            default=None,
            help="Override auto-generated filename. Cannot be combined with --split-by.",
        )(func)
        func = click.option(
            "--output-dir",
            "-d",
            default=".",
            show_default=True,
            help="Directory to write output files.",
        )(func)
        func = datatype_converter_option(func)
        func = template_option(func)
        func = export_format_option()(func)
        return func

    return decorator


def build_export_options(
    *,
    resource: str,
    resource_id: str,
    filters: tuple[str, ...],
    properties: list[str] | None,
    fmt: str | None,
    template: str | None,
    output_dir: str,
    output_file: str | None,
    split_by: str | None,
    filename_template: str | None,
    overwrite: bool,
    dry_run: bool,
    datatype_converter: str | None = None,
) -> GetOptions:
    from pathlib import Path

    from katalogue.rendering import auto_filename

    if output_file:
        out = _output_options(
            fmt,
            template=template,
            output_file=output_file,
            overwrite=overwrite,
            dry_run=dry_run,
        )
    elif split_by:
        out = _output_options(
            fmt,
            template=template,
            output_dir=output_dir,
            split_by=split_by,
            filename_template=filename_template,
            overwrite=overwrite,
            dry_run=dry_run,
        )
    else:
        ext = _export_extension(fmt, template)
        filename = auto_filename(f"{resource}-{resource_id}", extension=ext)
        auto_file = str(Path(output_dir) / filename)
        out = _output_options(
            fmt,
            template=template,
            output_file=auto_file,
            overwrite=overwrite,
            dry_run=dry_run,
        )
    return GetOptions(
        resource_id=resource_id,
        filters=list(filters) or None,
        properties=properties,
        include_children=True,
        datatype_converter=datatype_converter,
        output=out,
    )


def get_output_options(default_format: str = "json") -> Callable[[Any], Any]:
    def decorator(func: Any) -> Any:
        func = click.option(
            "--dry-run",
            is_flag=True,
            default=False,
            help="Show planned output files without writing them.",
        )(func)
        func = click.option(
            "--overwrite",
            is_flag=True,
            default=False,
            help="Overwrite existing output files.",
        )(func)
        func = click.option(
            "--output-file",
            "-o",
            default=None,
            help="Write rendered output to this file.",
        )(func)
        func = click.option(
            "--output-dir",
            "-d",
            default=None,
            help="Directory for split rendered output files.",
        )(func)
        func = click.option(
            "--filename-template",
            default=None,
            help="Jinja2 expression used to name split output files.",
        )(func)
        func = click.option(
            "--split-by",
            "-s",
            default=None,
            help="Split hierarchical output by resource level.",
        )(func)
        func = click.option(
            "--include-children",
            is_flag=True,
            default=False,
            help="Fetch the resource and its child resources.",
        )(func)
        func = datatype_converter_option(func)
        func = template_option(func)
        func = format_option(default_format)(func)
        return func

    return decorator
