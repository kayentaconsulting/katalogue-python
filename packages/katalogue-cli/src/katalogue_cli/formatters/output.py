"""Output formatters for katalogue-cli."""

from __future__ import annotations

from typing import Any

from katalogue.formatters import (
    format_compact_json,
    format_descriptions_to_plaintext,
    format_json,
)
from katalogue.utils import unwrap_list

__all__ = [
    "format_json",
    "format_compact_json",
    "format_descriptions_to_plaintext",
    "format_output",
    "format_list_table",
    "format_grouped_table",
    "format_table",
]


def format_table(data: dict[str, Any]) -> str:
    lines: list[str] = []

    meta = data.get("meta") or {}
    if meta:
        if env := meta.get("katalogue_env"):
            lines.append(f"Environment:  {env}")
        if version := meta.get("katalogue_version"):
            lines.append(f"Version:      {version}")
        if ts := meta.get("created_timestamp"):
            lines.append(f"Exported:     {ts}")
        if lines:
            lines.append("")

    inner = data.get("data", data)
    if isinstance(inner, dict):
        _format_dict(inner, lines)
    elif isinstance(inner, list):
        for item in inner:
            _format_dict(item, lines)
            lines.append("")

    return "\n".join(lines).rstrip()


_MAX_COL_WIDTH = 60


def _cell(value: Any) -> str:
    text = str(format_descriptions_to_plaintext(value) or "")
    if len(text) > _MAX_COL_WIDTH:
        return text[:_MAX_COL_WIDTH] + "…"
    return text


def format_list_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No results."

    columns = list(rows[0].keys())
    col_widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            col_widths[col] = max(col_widths[col], len(_cell(row.get(col))))

    header = "  ".join(col.ljust(col_widths[col]) for col in columns)
    separator = "  ".join("-" * col_widths[col] for col in columns)
    lines = [header, separator]
    for row in rows:
        line = "  ".join(_cell(row.get(col)).ljust(col_widths[col]) for col in columns)
        lines.append(line)

    return "\n".join(lines)


def _parent_label(id_field: str) -> str:
    """Derive a friendly label from an id field name: 'dataset_group_id' → 'dataset group'."""
    return id_field.removesuffix("_id").replace("_", " ")


def format_grouped_table(
    rows: list[dict[str, Any]], parents: list[tuple[str, str]]
) -> str:
    if not rows:
        return "No results."

    parent_fields = {f for id_f, name_f in parents for f in (id_f, name_f)}
    child_keys = [k for k in rows[0] if k not in parent_fields]

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = tuple(row.get(f) for id_f, name_f in parents for f in (id_f, name_f))
        groups.setdefault(key, []).append(row)

    lines: list[str] = []
    for key, group_rows in groups.items():
        it = iter(key)
        parts = []
        for id_field, _name_field in parents:
            gid, gname = next(it), next(it)
            parts.append(f"{_parent_label(id_field)}: {gname or gid}({gid})")
        lines.append(",  ".join(parts))
        child_rows = [{k: r[k] for k in child_keys if k in r} for r in group_rows]
        for line in format_list_table(child_rows).splitlines():
            lines.append(f"  {line}")
        lines.append("")

    return "\n".join(lines).rstrip()


def format_output(
    data: Any,
    fmt: str,
    group_by: list[tuple[str, str]] | None = None,
    wide: bool = False,
) -> str:
    """Route data to the correct formatter and return the output string.

    Unwraps API envelope dicts (e.g. {"systems": [...]}) for table output so
    callers never need to know about the wrapper shape.
    """
    if fmt == "json":
        return format_json(data)
    if fmt == "compact":
        return format_compact_json(data)

    data = unwrap_list(data)

    if isinstance(data, list) and group_by and not wide:
        return format_grouped_table(data, group_by)
    if isinstance(data, list):
        return format_list_table(data)
    return format_table(data)


def _format_dict(d: dict[str, Any], lines: list[str], indent: int = 0) -> None:
    prefix = "  " * indent
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            _format_dict(value, lines, indent + 1)
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}: [{len(value)} items]")
        else:
            lines.append(f"{prefix}{key}: {format_descriptions_to_plaintext(value)}")
