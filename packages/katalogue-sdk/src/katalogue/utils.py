"""Pure data-manipulation helpers for working with Katalogue API responses."""

from __future__ import annotations

from typing import Any


def unwrap_list(data: Any) -> list[Any]:
    """Unwrap a single-key wrapper dict to a plain list.

    The Katalogue API wraps list responses in a resource-keyed envelope
    (e.g. {"systems": [...]}). This lets callers treat both the raw API
    response and a plain list the same way without branching.

    {"systems": [{"id": 1}, {"id": 2}]}  ->  [{"id": 1}, {"id": 2}]
    [{"id": 1}, {"id": 2}]               ->  [{"id": 1}, {"id": 2}]  (unchanged)
    {"id": 1, "name": "A"}               ->  [{"id": 1, "name": "A"}]
    """
    if isinstance(data, dict):
        values = list(data.values())
        if len(data) == 1 and isinstance(values[0], list):
            return values[0]
    return data if isinstance(data, list) else [data]


def filter_fields(data: Any, fields: list[str] | None) -> Any:
    """Keep only the requested fields from a dict or list of dicts.

    API responses contain many fields that are rarely needed together.
    This lets callers select a subset for display or downstream processing
    without iterating manually. Wrapper dicts (e.g. {"systems": [...]}) are
    unwrapped to a plain list when fields are requested.

    # list of dicts
    filter_fields([{"id": 1, "name": "A", "extra": "x"}], ["id", "name"])
    -> [{"id": 1, "name": "A"}]

    # wrapper dict — unwrapped then filtered
    filter_fields({"systems": [{"id": 1, "name": "A", "extra": "x"}]}, ["id", "name"])
    -> [{"id": 1, "name": "A"}]

    # plain dict
    filter_fields({"id": 1, "name": "A", "extra": "x"}, ["id", "name"])
    -> {"id": 1, "name": "A"}

    # fields=None — data returned unchanged
    filter_fields([{"id": 1}], None)
    -> [{"id": 1}]
    """
    if not fields:
        return data

    if isinstance(data, dict):
        values = list(data.values())
        if len(data) == 1 and isinstance(values[0], list):
            return filter_fields(values[0], fields)
        return {f: data[f] for f in fields if f in data}

    if isinstance(data, list):
        return [{f: row[f] for f in fields if f in row} for row in data]

    return data


def filter_resultset(data: Any, key: str, value: Any) -> list[Any]:
    """Keep only rows where data[key] == value. Unwraps wrapper dicts first.

    List endpoints return all records for a resource type. This lets callers
    filter client-side when the API does not expose a query parameter for the
    desired field — e.g. filtering fields by dataset_id from a full field list.

    filter_resultset([{"id": 1, "type": "db"}, {"id": 2, "type": "api"}], "type", "db")
    -> [{"id": 1, "type": "db"}]

    filter_resultset({"fields": [{"id": 1, "dataset_id": "ds-1"}, {"id": 2, "dataset_id": "ds-2"}]}, "dataset_id", "ds-1")
    -> [{"id": 1, "dataset_id": "ds-1"}]
    """
    rows = unwrap_list(data)
    return [row for row in rows if row.get(key) == value]


def sort_resultset(data: list[Any], sort: list[dict[str, str]] | None) -> list[Any]:
    """Sort a result set by one or more columns. Null values are always sorted last.

    Columns are applied in order — the first entry in the list is the most
    significant sort key. Accepts "asc" or "desc" per column.

    sort_resultset(rows, [{"name": "asc"}])
    -> rows sorted by name ascending, nulls last

    sort_resultset(rows, [{"type": "desc"}, {"name": "asc"}])
    -> rows sorted by type descending, then name ascending within each type
    """
    if not sort:
        return data

    result = list(data)
    for spec in reversed(sort):
        for col, direction in spec.items():
            reverse = direction.lower() == "desc"
            non_null = [row for row in result if row.get(col) is not None]
            null_rows = [row for row in result if row.get(col) is None]
            non_null.sort(key=lambda row: row[col], reverse=reverse)  # type: ignore[index]
            result = non_null + null_rows
    return result
