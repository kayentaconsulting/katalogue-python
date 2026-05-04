"""Jinja2 template loading and rendering for export formats."""

from __future__ import annotations

import re
from typing import Any

from jinja2 import StrictUndefined, Template
from jinja2.sandbox import SandboxedEnvironment

from katalogue.template_registry import (
    get_template_default_format,
    looks_like_template_path as _looks_like_template_path,
    resolve_template_source,
)


STANDARD_FORMATS: frozenset[str] = frozenset(
    {"json", "table", "compact", "json-compact", "yaml", "yml", "csv"}
)


def is_template_format(fmt: str) -> bool:
    return fmt not in STANDARD_FORMATS


def looks_like_template_path(value: str) -> bool:
    return _looks_like_template_path(value)


def _env() -> SandboxedEnvironment:
    return SandboxedEnvironment(
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


def load_template(name_or_path: str) -> Template:
    """Load a built-in template by name, or a custom .j2 file by path."""
    env = _env()
    source, _ = resolve_template_source(name_or_path)
    return env.from_string(source)


def get_template_extension(fmt: str) -> str:
    """Return the natural output format for a template reference."""
    return get_template_default_format(fmt)


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
