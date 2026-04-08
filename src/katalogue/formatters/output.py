"""Output formatters for katalogue-cli."""

from __future__ import annotations

import json
from typing import Any


def format_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def format_compact_json(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"), default=str)


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


def format_list_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No results."

    columns = list(rows[0].keys())
    col_widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            val = str(row.get(col) or "")
            col_widths[col] = max(col_widths[col], len(val))

    header = "  ".join(col.ljust(col_widths[col]) for col in columns)
    separator = "  ".join("-" * col_widths[col] for col in columns)
    lines = [header, separator]
    for row in rows:
        line = "  ".join(
            str(row.get(col) or "").ljust(col_widths[col]) for col in columns
        )
        lines.append(line)

    return "\n".join(lines)


def _format_dict(d: dict[str, Any], lines: list[str], indent: int = 0) -> None:
    prefix = "  " * indent
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            _format_dict(value, lines, indent + 1)
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}: [{len(value)} items]")
        else:
            lines.append(f"{prefix}{key}: {value}")
