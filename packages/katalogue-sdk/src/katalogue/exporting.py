"""Hierarchical catalog export — flattening, assembly, and level-scoped filtering."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from katalogue.filters import Filter, apply_filter

if TYPE_CHECKING:
    from katalogue.client.api import KatalogueClient

# Known level names used to parse dotted filter paths.
_LEVEL_NAMES: frozenset[str] = frozenset(
    {"system", "datasource", "dataset_group", "dataset", "field", "glossary"}
)
# Singular resource keys present in the flat shape.
_SINGULAR_KEYS: frozenset[str] = frozenset(
    {"system", "datasource", "dataset_group", "dataset", "glossary"}
)
# List collection keys present in the flat shape.
_LIST_KEYS: frozenset[str] = frozenset(
    {"datasources", "dataset_groups", "datasets", "fields", "terms"}
)
# Metadata keys always preserved regardless of field selection.
_META_KEYS: frozenset[str] = frozenset({"resource", "id"})


# ---------------------------------------------------------------------------
# Flattening
# ---------------------------------------------------------------------------


def flatten_system_export(api_response: dict[str, Any]) -> dict[str, Any]:
    """Normalise the nested system-export API response to the flat SDK shape."""
    inner = api_response.get("data", api_response)
    if isinstance(inner, dict) and isinstance(inner.get("system"), dict):
        system_source = inner["system"]
        datasources_source = inner.get(
            "datasources", system_source.get("datasources", [])
        )
    else:
        system_source = inner if isinstance(inner, dict) else {}
        datasources_source = (
            inner.get("datasources", []) if isinstance(inner, dict) else []
        )

    system = {k: v for k, v in system_source.items() if k != "datasources"}
    datasources: list[dict[str, Any]] = []
    dataset_groups: list[dict[str, Any]] = []
    datasets: list[dict[str, Any]] = []
    fields: list[dict[str, Any]] = []

    for datasource in datasources_source:
        datasource_id = datasource.get("datasource_id")
        datasources.append(
            {k: v for k, v in datasource.items() if k != "dataset_groups"}
        )
        for group in datasource.get("dataset_groups", []):
            group_id = group.get("dataset_group_id")
            dataset_groups.append(
                {
                    **{k: v for k, v in group.items() if k != "datasets"},
                    "datasource_id": datasource_id,
                }
            )
            for dataset in group.get("datasets", []):
                dataset_id = dataset.get("dataset_id")
                dataset_name = dataset.get("dataset_name", "")
                datasets.append(
                    {
                        **{k: v for k, v in dataset.items() if k != "fields"},
                        "dataset_group_id": group_id,
                    }
                )
                for field in dataset.get("fields", []):
                    normalized = dict(field)
                    normalized["dataset_id"] = dataset_id
                    normalized["dataset_name"] = dataset_name
                    if "field_is_pii" in normalized and "is_pii" not in normalized:
                        normalized["is_pii"] = normalized["field_is_pii"]
                    if (
                        "field_datatype" in normalized
                        and "datatype_fullname" not in normalized
                    ):
                        normalized["datatype_fullname"] = normalized["field_datatype"]
                    fields.append(normalized)

    return {
        "system": system,
        "datasources": datasources,
        "dataset_groups": dataset_groups,
        "datasets": datasets,
        "fields": fields,
    }


# ---------------------------------------------------------------------------
# Hierarchical assembly helpers
# ---------------------------------------------------------------------------


def _unwrap_list(response: Any, resource: str) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        value = response.get(f"{resource}s")
        if isinstance(value, list):
            return value
    return []


def _unwrap_single(response: Any, resource: str) -> dict[str, Any]:
    if isinstance(response, dict):
        if isinstance(response.get(resource), dict):
            return response[resource]
        if f"{resource}s" not in response:
            return response
    rows = _unwrap_list(response, resource)
    return rows[0] if rows else {}


def _collect_children(
    client: "KatalogueClient",
    child_resource: str,
    parent_resource: str,
    parents: list[dict[str, Any]],
    parent_id_field: str,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for parent in parents:
        parent_id = parent.get(parent_id_field)
        if parent_id is None:
            continue
        children = _unwrap_list(
            client.list_by_parent(child_resource, parent_resource, parent_id),
            child_resource,
        )
        for child in children:
            row = dict(child)
            row.setdefault(parent_id_field, parent_id)
            if child_resource == "field":
                row.setdefault("dataset_name", parent.get("dataset_name", ""))
            result.append(row)
    return result


# ---------------------------------------------------------------------------
# Public assembly functions
# ---------------------------------------------------------------------------


def assemble_system(
    client: "KatalogueClient", resource_id: int | str
) -> dict[str, Any]:
    flat = flatten_system_export(client.get_system_export(resource_id))
    return {"resource": "system", "id": str(resource_id), **flat}


def assemble_datasource(
    client: "KatalogueClient", resource_id: int | str
) -> dict[str, Any]:
    datasource = _unwrap_single(
        client.get_resource("datasource", resource_id), "datasource"
    )
    datasource_id = datasource.get("datasource_id", resource_id)
    system_id = datasource.get("system_id")
    system: dict[str, Any] = (
        _unwrap_single(client.get_resource("system", system_id), "system")
        if system_id is not None
        else {}
    )
    dataset_groups = _unwrap_list(
        client.list_by_parent("dataset_group", "datasource", datasource_id),
        "dataset_group",
    )
    dataset_groups = [
        {**row, "datasource_id": row.get("datasource_id", datasource_id)}
        for row in dataset_groups
    ]
    datasets = _collect_children(
        client, "dataset", "dataset_group", dataset_groups, "dataset_group_id"
    )
    fields = _collect_children(client, "field", "dataset", datasets, "dataset_id")
    return {
        "resource": "datasource",
        "id": str(resource_id),
        "system": system,
        "datasource": datasource,
        "dataset_groups": dataset_groups,
        "datasets": datasets,
        "fields": fields,
    }


def assemble_dataset_group(
    client: "KatalogueClient", resource_id: int | str
) -> dict[str, Any]:
    dataset_group = _unwrap_single(
        client.get_resource("dataset_group", resource_id), "dataset_group"
    )
    group_id = dataset_group.get("dataset_group_id", resource_id)
    datasource_id = dataset_group.get("datasource_id")
    datasource: dict[str, Any] = (
        _unwrap_single(client.get_resource("datasource", datasource_id), "datasource")
        if datasource_id is not None
        else {}
    )
    system_id = datasource.get("system_id") if datasource else None
    system: dict[str, Any] = (
        _unwrap_single(client.get_resource("system", system_id), "system")
        if system_id is not None
        else {}
    )
    datasets = _unwrap_list(
        client.list_by_parent("dataset", "dataset_group", group_id), "dataset"
    )
    datasets = [
        {**row, "dataset_group_id": row.get("dataset_group_id", group_id)}
        for row in datasets
    ]
    fields = _collect_children(client, "field", "dataset", datasets, "dataset_id")
    return {
        "resource": "dataset_group",
        "id": str(resource_id),
        "system": system,
        "datasource": datasource,
        "dataset_group": dataset_group,
        "datasets": datasets,
        "fields": fields,
    }


def assemble_dataset(
    client: "KatalogueClient", resource_id: int | str
) -> dict[str, Any]:
    dataset = _unwrap_single(client.get_resource("dataset", resource_id), "dataset")
    dataset_id = dataset.get("dataset_id", resource_id)
    group_id = dataset.get("dataset_group_id")
    dataset_group: dict[str, Any] = (
        _unwrap_single(client.get_resource("dataset_group", group_id), "dataset_group")
        if group_id is not None
        else {}
    )
    datasource_id = dataset_group.get("datasource_id") if dataset_group else None
    datasource: dict[str, Any] = (
        _unwrap_single(client.get_resource("datasource", datasource_id), "datasource")
        if datasource_id is not None
        else {}
    )
    system_id = datasource.get("system_id") if datasource else None
    system: dict[str, Any] = (
        _unwrap_single(client.get_resource("system", system_id), "system")
        if system_id is not None
        else {}
    )
    fields = _unwrap_list(
        client.list_by_parent("field", "dataset", dataset_id), "field"
    )
    fields = [
        {
            **row,
            "dataset_id": row.get("dataset_id", dataset_id),
            "dataset_name": row.get("dataset_name", dataset.get("dataset_name", "")),
        }
        for row in fields
    ]
    return {
        "resource": "dataset",
        "id": str(resource_id),
        "system": system,
        "datasource": datasource,
        "dataset_group": dataset_group,
        "dataset": dataset,
        "fields": fields,
    }


def assemble_glossary(
    client: "KatalogueClient", resource_id: int | str
) -> dict[str, Any]:
    response = client.get_glossary_export(resource_id)
    payload = response.get("data", response) if isinstance(response, dict) else response
    glossary: dict[str, Any] = {}
    terms: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        glossary = payload.get("glossary", {})
        terms_value = payload.get("terms", [])
        terms = terms_value if isinstance(terms_value, list) else []
    return {
        "resource": "glossary",
        "id": str(resource_id),
        "glossary": glossary,
        "terms": terms,
    }


# ---------------------------------------------------------------------------
# Hierarchical filter application
# ---------------------------------------------------------------------------


def _parse_level_key(path: str, root_resource: str) -> tuple[str, str]:
    """Split dotted filter path into (level, key_within_row).

    'dataset.name'           → ('dataset', 'name')
    'field.is_pii'           → ('field', 'is_pii')
    'system.custom.code'     → ('system', 'custom.code')
    'is_pii' (bare)          → (root_resource, 'is_pii')
    """
    dot_pos = path.find(".")
    if dot_pos >= 0:
        candidate = path[:dot_pos]
        if candidate in _LEVEL_NAMES:
            return candidate, path[dot_pos + 1 :]
    return root_resource, path


def _row_matches(row: dict[str, Any], key: str, f: Filter) -> bool:
    """Apply filter f to row using key (level-stripped) instead of f.path."""
    if key == f.path:
        return apply_filter(row, f)
    # Construct a new Filter with the stripped key.
    return apply_filter(row, Filter(path=key, operator=f.operator, value=f.value))


def _group_filters(
    filters: list[Filter], root_resource: str
) -> dict[str, list[tuple[str, Filter]]]:
    """Group filters by level, each entry is (key_within_row, filter)."""
    grouped: dict[str, list[tuple[str, Filter]]] = {}
    for f in filters:
        level, key = _parse_level_key(f.path, root_resource)
        grouped.setdefault(level, []).append((key, f))
    return grouped


def _all_match(row: dict[str, Any], predicates: list[tuple[str, Filter]]) -> bool:
    return all(_row_matches(row, key, f) for key, f in predicates)


def _empty_shape(data: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(data)
    for k in list(result):
        if k in _SINGULAR_KEYS:
            result[k] = None
        elif k in _LIST_KEYS:
            result[k] = []
    return result


def apply_hierarchical_filters(
    data: dict[str, Any],
    filters: list[Filter],
    root_resource: str,
) -> dict[str, Any]:
    """Apply level-scoped filters to a flat canonical export dict.

    Pruning order (innermost first):
    1. fields
    2. datasets (remove rows not matching; also remove orphaned by field filter)
    3. dataset_groups (remove orphaned by dataset/field filter)
    4. datasources (remove orphaned)
    5. singular dicts (system/datasource/...) — if no match, zero entire shape
    """
    if not filters:
        return data

    result = deepcopy(data)
    grouped = _group_filters(filters, root_resource)

    # Singular resource levels — if no match, return zeroed shape.
    for level in list(_LEVEL_NAMES):
        if level in grouped and isinstance(result.get(level), dict):
            if not _all_match(result[level], grouped[level]):
                empty = _empty_shape(result)
                # Preserve non-singular, non-list metadata keys
                for k in _META_KEYS:
                    if k in data:
                        empty[k] = data[k]
                return empty

    # Field-level filter
    if "field" in grouped:
        result["fields"] = [
            row for row in result.get("fields", []) if _all_match(row, grouped["field"])
        ]

    # Dataset-level filter
    if "dataset" in grouped and "datasets" in result:
        result["datasets"] = [
            row
            for row in result.get("datasets", [])
            if _all_match(row, grouped["dataset"])
        ]

    # Prune datasets orphaned by field filter
    if "field" in grouped and "datasets" in result:
        live_dataset_ids = {row.get("dataset_id") for row in result.get("fields", [])}
        result["datasets"] = [
            row
            for row in result["datasets"]
            if row.get("dataset_id") in live_dataset_ids
        ]

    # Dataset-group-level filter
    if "dataset_group" in grouped and "dataset_groups" in result:
        result["dataset_groups"] = [
            row
            for row in result.get("dataset_groups", [])
            if _all_match(row, grouped["dataset_group"])
        ]
        live_group_ids = {
            row.get("dataset_group_id") for row in result["dataset_groups"]
        }
        if "datasets" in result:
            result["datasets"] = [
                row
                for row in result["datasets"]
                if row.get("dataset_group_id") in live_group_ids
            ]
        if "fields" in result:
            live_dataset_ids2 = {
                row.get("dataset_id") for row in result.get("datasets", [])
            }
            result["fields"] = [
                row
                for row in result["fields"]
                if row.get("dataset_id") in live_dataset_ids2
            ]

    # Prune dataset_groups orphaned by dataset/field filter
    if {"dataset", "field"} & grouped.keys() and "dataset_groups" in result:
        live_group_ids2 = {
            row.get("dataset_group_id") for row in result.get("datasets", [])
        }
        result["dataset_groups"] = [
            row
            for row in result.get("dataset_groups", [])
            if row.get("dataset_group_id") in live_group_ids2
        ]

    # Datasource-level filter
    if "datasource" in grouped and "datasources" in result:
        result["datasources"] = [
            row
            for row in result.get("datasources", [])
            if _all_match(row, grouped["datasource"])
        ]

    # Prune datasources orphaned by lower-level filters
    if {
        "dataset_group",
        "dataset",
        "field",
    } & grouped.keys() and "datasources" in result:
        live_ds_ids = {
            row.get("datasource_id") for row in result.get("dataset_groups", [])
        }
        result["datasources"] = [
            row
            for row in result.get("datasources", [])
            if row.get("datasource_id") in live_ds_ids
        ]

    return result
