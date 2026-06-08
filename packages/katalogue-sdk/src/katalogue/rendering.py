"""Jinja2 template loading and rendering for export formats."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import (
    ChoiceLoader,
    FileSystemLoader,
    PackageLoader,
    StrictUndefined,
    Template,
)
from jinja2.sandbox import SandboxedEnvironment

from katalogue.template_registry import (
    get_template_default_format,
    load_macro_paths,
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


def field_type(f: dict[str, Any]) -> str:
    """Resolve a field's datatype using converted → fullname → raw fallback."""
    return (
        f.get("datatype_converted")
        or f.get("datatype_fullname")
        or f.get("field_datatype")
        or ""
    )


def field_desc(f: dict[str, Any]) -> str:
    """Resolve a field's description using source_description → description fallback."""
    return f.get("field_source_description") or f.get("description") or ""


def field_is_pii(f: dict[str, Any]) -> bool:
    """True if either PII flag is set."""
    return bool(f.get("is_pii") or f.get("field_is_pii"))


def field_is_primary_key(f: dict[str, Any]) -> bool:
    """True if the field is flagged as a primary key."""
    return bool(f.get("field_is_primary_key"))


def dataset_desc(ds: dict[str, Any]) -> str:
    """Resolve a dataset's description using dataset_description → description fallback."""
    return ds.get("dataset_description") or ds.get("description") or ""


def _build_fields_tree(
    fields: list[dict[str, Any]], dataset_id: Any = None
) -> list[dict[str, Any]]:
    """Reshape a flat field list into a parent_field_id-nested tree.

    Each returned dict is a shallow copy of the source field with two
    derived keys attached: `children` (list of child field dicts, also
    nested) and `field_path` (the dotted path from the root, e.g.
    `address.city`).  Orphaned children (parent_field_id pointing outside
    the pool) are promoted to roots so they're not silently dropped.
    """
    pool = [
        f for f in fields if dataset_id is None or f.get("dataset_id") == dataset_id
    ]
    known_ids: set[Any] = {f.get("field_id") for f in pool}
    by_parent: dict[Any, list[dict[str, Any]]] = {}
    for f in pool:
        pid = f.get("parent_field_id")
        if pid is not None and pid not in known_ids:
            pid = None
        by_parent.setdefault(pid, []).append(f)

    def attach(node: dict[str, Any], prefix: str) -> dict[str, Any]:
        copy = dict(node)
        name = str(copy.get("field_name") or "")
        path = f"{prefix}.{name}" if prefix else name
        copy["field_path"] = path
        copy["children"] = [
            attach(c, path) for c in by_parent.get(node.get("field_id"), [])
        ]
        return copy

    return [attach(r, "") for r in by_parent.get(None, [])]


_HELPER_GLOBALS: dict[str, Any] = {
    "field_type": field_type,
    "field_desc": field_desc,
    "field_is_pii": field_is_pii,
    "field_is_primary_key": field_is_primary_key,
    "dataset_desc": dataset_desc,
}


def _env(extra_search_paths: list[Path] | None = None) -> SandboxedEnvironment:
    loaders: list[Any] = [PackageLoader("katalogue", "templates")]
    if extra_search_paths:
        loaders.append(FileSystemLoader([str(p) for p in extra_search_paths]))
    env = SandboxedEnvironment(
        loader=ChoiceLoader(loaders),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    env.globals.update(_HELPER_GLOBALS)
    return env


def _extra_search_paths(name_or_path: str) -> list[Path]:
    paths: list[Path] = []
    if _looks_like_template_path(name_or_path):
        template_dir = Path(name_or_path).expanduser().resolve().parent
        paths.append(template_dir)
        paths.extend(load_macro_paths(start_dir=template_dir))
    else:
        paths.extend(load_macro_paths())
    return paths


def load_template(name_or_path: str) -> Template:
    """Load a built-in template by name, or a custom .j2 file by path."""
    source, _ = resolve_template_source(name_or_path)
    return _env(_extra_search_paths(name_or_path)).from_string(source)


def get_template_extension(fmt: str) -> str:
    """Return the natural output format for a template reference."""
    return get_template_default_format(fmt)


def render_template(template: Template, context: dict[str, Any]) -> str:
    fields = context.get("fields") or []

    def fields_tree(dataset_id: Any = None) -> list[dict[str, Any]]:
        return _build_fields_tree(fields, dataset_id)

    return template.render(**context, fields_tree=fields_tree)


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
