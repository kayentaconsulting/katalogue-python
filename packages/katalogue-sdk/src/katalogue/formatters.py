"""Serialization formatters for Katalogue API result sets."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

import yaml


def format_json(data: Any) -> str:
    """Serialize data to a pretty-printed JSON string.

    format_json([{"id": 1, "name": "CDP"}])
    -> '[\\n  {\\n    "id": 1,\\n    "name": "CDP"\\n  }\\n]'
    """
    return json.dumps(data, indent=2, default=str)


def format_yaml(data: Any) -> str:
    """Serialize data to a YAML string.

    format_yaml([{"id": 1, "name": "A"}]) -> "- id: 1\\n  name: A\\n"
    """
    return yaml.dump(
        data, allow_unicode=True, sort_keys=False, default_flow_style=False
    )


def format_compact_json(data: Any) -> str:
    """Serialize data to a compact JSON string with no whitespace.

    format_compact_json([{"id": 1, "name": "CDP"}])
    -> '[{"id":1,"name":"CDP"}]'
    """
    return json.dumps(data, separators=(",", ":"), default=str)


def format_descriptions_to_plaintext(data: Any) -> Any:
    """Convert Draft.js rich-text JSON strings to plain text throughout a result set.

    Katalogue description fields may contain Draft.js JSON (a legacy rich-text
    format). This function extracts the readable text from those fields so
    callers receive clean strings without needing to parse the format themselves.
    Applied recursively — works on a single value, a dict, or a list of dicts.

    # single Draft.js string
    format_descriptions_to_plaintext('{"blocks":[{"text":"Hello world"}],"entityMap":{}}')
    -> "Hello world"

    # plain string — returned unchanged
    format_descriptions_to_plaintext("just text")
    -> "just text"

    # list of dicts — applied to all string values
    format_descriptions_to_plaintext([{"name": "A", "description": "<draftjs json>"}])
    -> [{"name": "A", "description": "extracted text"}]
    """
    if isinstance(data, str):
        return _draftjs_to_text(data)
    if isinstance(data, list):
        return [format_descriptions_to_plaintext(item) for item in data]
    if isinstance(data, dict):
        return {k: format_descriptions_to_plaintext(v) for k, v in data.items()}
    return data


def _draftjs_to_text(value: str) -> str:
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        return value
    if not isinstance(parsed, dict) or "blocks" not in parsed:
        return value
    return " ".join(b.get("text", "") for b in parsed["blocks"] if b.get("text"))


_MAX_COL_WIDTH = 60


def _cell(value: Any) -> str:
    text = str(format_descriptions_to_plaintext(value) or "")
    return text[:_MAX_COL_WIDTH] + "…" if len(text) > _MAX_COL_WIDTH else text


def format_table(data: Any) -> str:
    """Render data as a plain-text table or key:value block.

    format_table([{"id": 1, "name": "A"}]) -> "id  name\\n--  ----\\n1   A"
    format_table([])                        -> "No results."
    format_table({"id": 1, "name": "A"})   -> "id: 1\\nname: A"
    """
    if isinstance(data, list):
        if not data:
            return "No results."
        columns = list(data[0].keys())
        col_widths = {col: len(col) for col in columns}
        for row in data:
            for col in columns:
                col_widths[col] = max(col_widths[col], len(_cell(row.get(col))))
        header = "  ".join(col.ljust(col_widths[col]) for col in columns)
        separator = "  ".join("-" * col_widths[col] for col in columns)
        lines = [header, separator]
        for row in data:
            lines.append(
                "  ".join(_cell(row.get(col)).ljust(col_widths[col]) for col in columns)
            )
        return "\n".join(lines)
    if isinstance(data, dict):
        return "\n".join(
            f"{k}: {format_descriptions_to_plaintext(v)}" for k, v in data.items()
        )
    return str(data)


def _scalar(value: Any) -> str | int | float | bool | None:
    """Convert a value to a CSV-safe scalar."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    if isinstance(value, str):
        return value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return value


def _prefix_system(system: dict[str, Any]) -> dict[str, Any]:
    return {
        k if k.startswith("system_") else f"system_{k}": v for k, v in system.items()
    }


def _flatten_glossary_for_csv(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a nested glossary export to one CSV row per asset.

    Walks the ``business_terms`` tree (plus any root-level orphan
    ``field_descriptions``) depth-first, emitting a row for every business term
    and field description. Glossary metadata is denormalized into each row and
    the node's ``full_path`` is surfaced as a ``path`` column. A field
    description attached to several terms yields one row per attachment.
    """
    glossary = data.get("glossary") or {}
    glossary_cols = {
        "glossary_id": glossary.get("glossary_id"),
        "glossary_name": glossary.get("glossary_name"),
    }

    rows: list[dict[str, Any]] = []

    def emit(asset: dict[str, Any]) -> None:
        fields = {
            k: v
            for k, v in asset.items()
            if k not in ("business_terms", "field_descriptions", "full_path")
        }
        merged = {**glossary_cols, "path": asset.get("full_path") or "", **fields}
        rows.append({k: _scalar(v) for k, v in merged.items()})

    def walk(term: dict[str, Any]) -> None:
        emit(term)
        for fd in term.get("field_descriptions") or []:
            emit(fd)
        for child in term.get("business_terms") or []:
            walk(child)

    for root in data.get("business_terms") or []:
        walk(root)
    for orphan in data.get("field_descriptions") or []:
        emit(orphan)

    return rows


def _flatten_for_csv(data: Any) -> list[dict[str, Any]]:
    """Flatten catalog data to a list of dicts for CSV serialization.

    Flat list[dict] → returned as-is.
    Hierarchical dict (from include-children export) → flattened to the lowest
    available level: fields > datasets > dataset_groups > datasources > singular resource.
    Parent values are denormalized into every child row.
    """
    if isinstance(data, list):
        return [{k: _scalar(v) for k, v in row.items()} for row in data]
    if not isinstance(data, dict):
        return [{"value": str(data)}]

    # Only flatten hierarchically for SDK-assembled data (always carries a
    # "resource" sentinel set by the assemble_* functions). Plain API responses
    # must not enter this path — they may contain keys like "fields" or
    # "datasources" that would cause incorrect multi-row expansion.
    if data.get("resource") not in {
        "system",
        "datasource",
        "dataset_group",
        "dataset",
        "glossary",
    }:
        # Unwrap single-key list envelopes (e.g. {"systems": [{...}]}).
        values = list(data.values())
        if len(data) == 1 and isinstance(values[0], list):
            return [{k: _scalar(v) for k, v in row.items()} for row in values[0]]
        for key in ("datasource", "dataset_group", "dataset", "field"):
            if isinstance(data.get(key), dict):
                return [{k: _scalar(v) for k, v in data[key].items()}]
        return [{k: _scalar(v) for k, v in data.items()}]

    # Glossary exports carry a nested business_terms tree, not the system-side
    # datasets/fields collections — flatten it to one row per asset.
    if data.get("resource") == "glossary":
        return _flatten_glossary_for_csv(data)

    fields = data.get("fields") or []
    datasets = data.get("datasets") or []
    dataset_groups = data.get("dataset_groups") or []
    datasources: list[dict[str, Any]] = data.get("datasources") or (
        [data["datasource"]] if isinstance(data.get("datasource"), dict) else []
    )

    system_row = _prefix_system(data.get("system") or {})
    ds_by_id = {d.get("datasource_id"): d for d in datasources}
    dg_by_id = {g.get("dataset_group_id"): g for g in dataset_groups}
    dt_by_id = {d.get("dataset_id"): d for d in datasets}

    def _row(*layers: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for layer in layers:
            merged.update(layer)
        return {k: _scalar(v) for k, v in merged.items()}

    if fields:
        rows = []
        for field in fields:
            dataset = dt_by_id.get(field.get("dataset_id"), {})
            dg = dg_by_id.get(dataset.get("dataset_group_id"), {})
            ds = ds_by_id.get(dg.get("datasource_id"), {})
            rows.append(_row(system_row, ds, dg, dataset, field))
        return rows

    if datasets:
        rows = []
        for dataset in datasets:
            dg = dg_by_id.get(dataset.get("dataset_group_id"), {})
            ds = ds_by_id.get(dg.get("datasource_id"), {})
            rows.append(_row(system_row, ds, dg, dataset))
        return rows

    if dataset_groups:
        rows = []
        for dg in dataset_groups:
            ds = ds_by_id.get(dg.get("datasource_id"), {})
            rows.append(_row(system_row, ds, dg))
        return rows

    if datasources:
        return [_row(system_row, ds) for ds in datasources]

    for key in ("datasource", "dataset_group", "dataset", "field"):
        if isinstance(data.get(key), dict):
            return [_row(system_row, data[key])]

    return [{k: _scalar(v) for k, v in data.items()}]


def format_csv(data: Any) -> str:
    """Serialize data to a CSV string, flattening hierarchical data to the lowest level.

    format_csv([{"id": 1, "name": "A"}]) -> "id,name\\n1,A\\n"
    """
    rows = _flatten_for_csv(data)
    if not rows:
        return ""
    fieldnames = list(dict.fromkeys(k for row in rows for k in row))
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, restval="", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def format_resultset(data: Any, fmt: str | None) -> Any:
    """Serialize a result set to the requested format, or return the Python object.

    fmt="json"                 -> pretty-printed JSON string
    fmt="compact"/"json-compact" -> compact JSON string, no whitespace
    fmt="yaml"/"yml"           -> YAML string
    fmt="csv"                  -> CSV string (hierarchical data flattened to lowest level)
    fmt="table"                -> plain-text table string
    fmt=None                   -> data returned as-is (Python dict or list)
    """
    if fmt == "json":
        return format_json(data)
    if fmt in ("compact", "json-compact"):
        return format_compact_json(data)
    if fmt in ("yaml", "yml"):
        return format_yaml(data)
    if fmt == "csv":
        return format_csv(data)
    if fmt == "table":
        return format_table(data)
    return data
