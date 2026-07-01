---
title: SDK options and results
description: GetOptions, OutputOptions, CatalogResult, WrittenFile, and Filter reference.
---

`client.get(resource, options)` is the single entry point for querying the catalog.
A `GetOptions` object controls routing, filtering, sorting, and output; the call
returns a `CatalogResult`. All filtering and sorting happen **client-side** after the
API fetch.

See [SDK client](/katalogue-python/sdk/client) for setup and authentication, and
[Filtering and selection](/katalogue-python/reference/filtering) for filter syntax shared with the CLI.

## Contents

- [The result object](#the-result-object)
- [Routing](#routing)
- [Querying: properties, sort, descriptions](#querying-properties-sort-descriptions)
- [Serialization formats](#serialization-formats)
- [Hierarchical retrieval](#hierarchical-retrieval)
- [GetOptions reference](#getoptions-reference)
- [OutputOptions reference](#outputoptions-reference)
- [Result models](#result-models)

## The result object

```python
result = client.get(resource, options=GetOptions(...))
# result.data          — filtered/sorted Python object (dict or list of dicts)
# result.raw           — unprocessed API response
# result.output        — formatted string (set when OutputOptions.format or .template is set)
# result.output_file   — path written to (set when OutputOptions.output_file is used)
# result.output_files  — list[WrittenFile] (set when OutputOptions.split_by is used)
# result.metadata["strategy"] — "single" | "list" | "list_by_parent" | "export_endpoint"
```

## Routing

The combination of `resource_id` and `parent_id` selects the behaviour:

| `resource_id` | `parent_id` | Behaviour |
|:---:|:---:|---|
| — | — | All records of the resource type |
| ✓ | — | Single record by ID |
| — | ✓ | All children of that parent |
| ✓ | ✓ | Single record, `None` if it doesn't belong to the parent |

`parent_id` is silently ignored for top-level resources (`system`, `glossary`).

```python
client.get("system")                                   # all systems
client.get("system", GetOptions(resource_id=1))        # one system
client.get("datasource", GetOptions(parent_id=1))      # datasources under system 1
client.get("field", GetOptions(resource_id=42, parent_id=10))  # field 42 if in dataset 10, else data=None
```

## Querying: properties, sort, descriptions

```python
# Select specific properties
client.get("system", GetOptions(properties=["system_id", "system_name"]))

# Multi-column sort. "asc"/"desc" are case-insensitive; nulls sort last.
client.get("field", GetOptions(sort=[{"dataset_name": "asc"}, {"field_name": "asc"}]))

# Filter client-side (see ../reference/filtering.md for the full operator list)
client.get("field", GetOptions(filters=["is_pii=true"]))

# Description fields are rich-text JSON — extract plain text
client.get("system", GetOptions(
    properties=["system_id", "system_name", "system_description"],
    format_descriptions_as_text=True,
))
```

Invalid input raises `ValueError`:

```python
client.get("ssystem")
# ValueError: Invalid resource 'ssystem'. Must be one of: dataset, dataset_group, datasource, field, glossary, system

client.get("system", GetOptions(sort=[{"system_name": "ascending"}]))
# ValueError: Invalid sort direction 'ascending' ... Must be 'asc' or 'desc'.
```

## Serialization formats

Pass `OutputOptions(format=...)` to serialize the result into `result.output`.

```python
from katalogue import KatalogueClient, GetOptions, OutputOptions

result = client.get("system", GetOptions(output=OutputOptions(format="json")))
print(result.output)   # '[\n  {\n    "system_id": 1, ...'
```

Formats: `json`, `yaml` (or `yml`), `json-compact` (or `compact`), `csv`. For CSV,
hierarchical data is flattened to the lowest level with parent columns denormalized
into each row.

## Hierarchical retrieval

Pass `include_children=True` with `resource_id` to fetch a resource and all its
descendants in one call. The result is a flat canonical shape with each child level
in its own top-level list:

```python
result = client.get("system", GetOptions(resource_id=1, include_children=True))
# result.data -> {
#   "resource": "system",
#   "system": {"system_id": 1, ...},
#   "datasources": [...],
#   "dataset_groups": [...],
#   "datasets": [...],
#   "fields": [...],
# }
```

Supported for `system`, `datasource`, `dataset_group`, `dataset`, and `glossary`.
Hierarchical filters scope to the named level — only records at that level are
pruned, ancestors are retained:

```python
client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    filters=["field.is_pii=true"],   # keep only PII fields
))
```

Rendering this hierarchy through templates and splitting it into files is covered in
the [Exporting guide](/katalogue-python/guides/exporting).

## GetOptions reference

| Field | Type | Description |
|-------|------|-------------|
| `resource_id` | `int \| str \| None` | Fetch a single resource by ID |
| `parent_id` | `int \| str \| None` | Fetch all children of a parent |
| `filters` | `str \| list[str] \| list[Filter] \| None` | Client-side filter expressions |
| `properties` | `list[str] \| None` | Columns to keep in the result |
| `sort` | `list[dict[str, str]] \| None` | Multi-column sort, e.g. `[{"name": "asc"}]` |
| `include_children` | `bool` | Fetch resource and all descendants (default `False`) |
| `format_descriptions_as_text` | `bool` | Convert rich-text descriptions to plain text (default `False`) |
| `datatype_converter` | `str \| None` | Built-in name, registered name, or `.yaml`/`.yml` path — adds `datatype_converted` to each field. See [Datatype conversion](/katalogue-python/guides/datatype-conversion) |
| `output` | `OutputOptions` | Output rendering and file options |

## OutputOptions reference

| Field | Type | Description |
|-------|------|-------------|
| `format` | `str \| None` | `json`, `yaml`, `yml`, `json-compact`, `compact`, `csv` |
| `template` | `str \| None` | Built-in template name or path to a `.j2` file. See [Templates](/katalogue-python/guides/templates) |
| `output_file` | `str \| None` | Write output to this file path |
| `output_dir` | `str \| None` | Directory for split output files |
| `split_by` | `str \| None` | Split level: `datasource`, `dataset_group`, `dataset` |
| `filename_template` | `str \| None` | Jinja2 expression for naming split files |
| `overwrite` | `bool` | Overwrite existing files (default `False`) |
| `dry_run` | `bool` | Plan files without writing them (default `False`) |

Validation: `split_by` requires `include_children=True` and `output_dir`;
`output_file` and `output_dir` are mutually exclusive.

## Result models

**`CatalogResult`** — the envelope returned by `get()`:

| Field | Type | Description |
|-------|------|-------------|
| `data` | `Any` | Filtered/sorted Python object |
| `raw` | `Any \| None` | Unprocessed API response |
| `output` | `str \| None` | Rendered string output |
| `output_file` | `str \| None` | Path written (single-file output) |
| `output_files` | `list[WrittenFile]` | Files written (split output) |
| `metadata` | `dict[str, Any]` | Includes `metadata["strategy"]` |

**`WrittenFile`** — one entry per file in a split export: `path`, `split_key`,
`split_value`, `resource_type`.

**`Filter`** — a parsed filter expression: `path`, `operator`, `value`. You can
construct one directly or let `GetOptions(filters=[...])` parse strings for you. See
[Filtering and selection](/katalogue-python/reference/filtering).
