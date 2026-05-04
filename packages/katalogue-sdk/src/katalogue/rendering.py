"""Jinja2 template loading and rendering for export formats."""

from __future__ import annotations

import importlib.resources
import re
from pathlib import Path
from typing import Any

from jinja2 import StrictUndefined, Template
from jinja2.sandbox import SandboxedEnvironment

BUILTIN_TEMPLATES: dict[str, str] = {
    "dbt-source": "dbt_source.j2",
    "column-mapping": "column_mapping.j2",
    "json-template": "json_template.j2",
}

# Default file extension for auto-generated filenames per built-in template.
# Templates not listed here fall back to "yml".
BUILTIN_TEMPLATE_EXTENSIONS: dict[str, str] = {
    "json-template": "json",
}


def get_template_extension(fmt: str) -> str:
    """Return the default file extension for auto-generated filenames."""
    return BUILTIN_TEMPLATE_EXTENSIONS.get(fmt, "yml")


STANDARD_FORMATS: frozenset[str] = frozenset(
    {"json", "table", "compact", "json-compact", "yaml", "yml", "csv"}
)


def is_template_format(fmt: str) -> bool:
    return fmt not in STANDARD_FORMATS


def looks_like_template_path(value: str) -> bool:
    return value.endswith(".j2") or "/" in value or "\\" in value


def _env() -> SandboxedEnvironment:
    return SandboxedEnvironment(
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


def load_template(name_or_path: str) -> Template:
    """Load a built-in template by name, or a custom .j2 file by path."""
    env = _env()

    if name_or_path in BUILTIN_TEMPLATES:
        package = importlib.resources.files("katalogue.templates")
        source = (package / BUILTIN_TEMPLATES[name_or_path]).read_text(encoding="utf-8")
        return env.from_string(source)

    if looks_like_template_path(name_or_path):
        path = Path(name_or_path).expanduser()
        if path.suffix != ".j2":
            raise ValueError(
                f"Custom template paths must end in .j2 (got '{name_or_path}')."
            )
        if not path.exists():
            raise FileNotFoundError(f"Template file not found: {name_or_path}")
        return env.from_string(path.read_text(encoding="utf-8"))

    builtins = ", ".join(sorted(BUILTIN_TEMPLATES))
    raise ValueError(
        f"Unknown format '{name_or_path}'. Standard formats: json, table, compact. "
        f"Built-in templates: {builtins}. Or provide a path to a .j2 file."
    )


def render_template(template: Template, context: dict[str, Any]) -> str:
    return template.render(**context)


def auto_filename(
    value: str | dict[str, Any],
    split_by: str | None = None,
    extension: str = "yml",
) -> str:
    """Derive a safe slug filename from a resource name or context dict."""
    if isinstance(value, str):
        name = value
    else:
        name = _name_from_context(value, split_by)
    slug = re.sub(r"[^a-z0-9-]+", "-", str(name).lower()).strip("-")
    return f"{slug or 'output'}.{extension}"


def _name_from_context(context: dict[str, Any], split_by: str | None) -> str:
    level = split_by or context.get("resource")
    if level:
        level = str(level).replace("-", "_")
    if level and isinstance(context.get(level), dict):
        row = context[level]
        return (
            row.get(f"{level}_name")
            or row.get("name")
            or row.get(f"{level}_id")
            or f"output_{level}"
        )
    system = context.get("system")
    if isinstance(system, dict):
        return system.get("system_name") or system.get("name") or "output"
    return "output"


def render_filename(template_expr: str, context: dict[str, Any]) -> str:
    return _env().from_string(template_expr).render(**context)
