---
title: Resources reference
description: Resource hierarchy, CLI vs SDK naming, default table columns, and response shape.
---

The catalog is a hierarchy of resources. This page describes the hierarchy, the
default columns shown in CLI tables, the field keys the built-in tooling relies on,
and the shape of a hierarchical response.

## Contents

- [Hierarchy](#hierarchy)
- [Naming: CLI vs SDK](#naming-cli-vs-sdk)
- [Default table columns](#default-table-columns)
- [Common field keys](#common-field-keys)
- [Hierarchical response shape](#hierarchical-response-shape)

## Hierarchy

The catalog has two independent hierarchies:

```
system
  └── datasource
        └── dataset_group
              └── dataset
                    └── field ── field_description (FK)
                                      │
glossary                              │ (reference table, many-to-many)
  └── business_term ─────────────────┘
```

Fields carry a `field_description_id` foreign key. Field descriptions are linked to
business terms via a many-to-many reference table — a field description may belong to
multiple business terms and vice versa.

Each resource (except `field`) can be fetched with its descendants via
`--include-children` (CLI) or `include_children=True` (SDK).

## Naming: CLI vs SDK

The CLI uses hyphens in resource names; the SDK uses underscores.

| CLI | SDK `resource` string |
|-----|-----------------------|
| `system` | `"system"` |
| `datasource` | `"datasource"` |
| `dataset-group` | `"dataset_group"` |
| `dataset` | `"dataset"` |
| `field` | `"field"` |
| `glossary` | `"glossary"` |
| `business-term` | `"business_term"` |
| `field-description` | `"field_description"` |

Split levels (`--split-by`, `OutputOptions.split_by`) always use the underscore form
(`dataset_group`).

## Default table columns

When `list` renders as a `table` and no `--properties` is given, these columns are
shown. Use `--wide` to show all properties, or `--properties` to choose your own.
(JSON, YAML, CSV, and compact output always return all properties.)

| Resource | Default columns |
|----------|-----------------|
| `system` | `system_id`, `system_name`, `system_type`, `system_description` |
| `datasource` | `datasource_id`, `datasource_name`, `datasource_type_name`, `datasource_description` |
| `dataset_group` | `dataset_group_id`, `dataset_group_name`, `dataset_group_description` |
| `dataset` | `dataset_id`, `dataset_name`, `dataset_type_name`, `dataset_description` |
| `field` | `field_id`, `field_name`, `field_description_name`, `field_source_description` |
| `glossary` | `glossary_id`, `glossary_name`, `glossary_description` |
| `business_term` | `business_term_id`, `business_term_name`, `glossary_name`, `business_term_description` |
| `field_description` | `field_description_name`, `field_role_name`, `is_pii`, `field_sensitivity_name`, `field_description_description` |

In `list` table output, child resources are grouped by their parent's `(id, name)`
columns — e.g. a `field` listing is grouped by system, datasource, dataset group,
and dataset.

## Common field keys

The exact keys depend on your Katalogue instance — use `katalogue <resource> keys` to
see what your API returns. The built-in templates and datatype conversion rely on
these keys:

| Key | Description |
|-----|-------------|
| `field_name` | Column/field name |
| `dataset_name` | Name of the parent dataset |
| `dataset_id` | ID of the parent dataset |
| `datatype_fullname` | Full data type string (preferred) |
| `field_datatype` | Fallback data type string |
| `datatype_converted` | Target-platform type — present only when a [datatype converter](/katalogue-python/guides/datatype-conversion) is active |
| `field_source_description` | Description from the source system (preferred) |
| `description` | Fallback description |
| `is_pii` | Boolean — field contains PII (preferred) |
| `field_is_pii` | Fallback PII flag |
| `field_is_primary_key` | Boolean — field is a primary key |

To discover every key on your data, render with the built-in `json-template` or run
the `keys` command:

```bash
katalogue dataset keys --format json
katalogue datasource export 5 --template json-template
```

## Hierarchical response shape

### System-side resources

`include_children` on system-side resources returns a flat canonical shape — each
child level in its own top-level list:

```json
{
  "resource": "system",
  "system": { "system_id": 1, "system_name": "..." },
  "datasources": [ ... ],
  "dataset_groups": [ ... ],
  "datasets": [ ... ],
  "fields": [ ... ]
}
```

This is the same context that [templates](/katalogue-python/guides/templates) receive when
rendering. Fields are a flat list linked by `parent_field_id`; the `fields_tree`
template helper reshapes them into a nested tree.

### Glossary-side resources

`business-term export` and `field-description export` return a different shape that
reflects the cross-hierarchy reference links.

**`business-term export <id>`** — returns the term with each linked field description
nested, and under each field description the physical fields where it appears (with
full datasource and system context):

```json
{
  "resource": "business_term",
  "id": "8",
  "business_term_name": "...",
  "field_descriptions": [
    {
      "field_description_id": 167,
      "field_description_name": "...",
      "is_pii": false,
      "fields": [
        {
          "field_name": "...",
          "dataset_name": "...",
          "datasource_name": "...",
          "system_name": "..."
        }
      ]
    }
  ]
}
```

**`field-description export <id>`** — returns the field description with the business
terms it is linked to and the physical fields where it appears:

```json
{
  "resource": "field_description",
  "id": "167",
  "field_description_name": "...",
  "is_pii": false,
  "business_terms": [
    {
      "business_term_id": 8,
      "business_term_name": "...",
      "glossary_id": 1,
      "glossary_name": "..."
    }
  ],
  "fields": [
    {
      "field_name": "...",
      "dataset_name": "...",
      "datasource_name": "...",
      "system_name": "..."
    }
  ]
}
```

**`glossary export <id>`** — returns the glossary metadata and a recursive
`business_terms` tree. Each term carries its own `field_descriptions` and any nested
child `business_terms`, mirroring the term hierarchy. A field description linked to
several terms appears once under each. `field_descriptions` at the top level is an
orphan bucket (normally empty):

```json
{
  "resource": "glossary",
  "id": "2",
  "glossary": { "glossary_id": 2, "glossary_name": "...", "glossary_description": "..." },
  "business_terms": [
    {
      "id": 15,
      "name": "Customer",
      "asset_type": "business_term",
      "full_path": "",
      "field_descriptions": [ { "id": 210, "name": "Customer ID", "asset_type": "field_description", "full_path": "Customer" } ],
      "business_terms": [
        {
          "id": 19,
          "name": "Sales Order",
          "full_path": "Customer::Sales Order",
          "field_descriptions": [ ... ],
          "business_terms": [ ... ]
        }
      ]
    }
  ],
  "field_descriptions": []
}
```

With `--format csv`, this tree is flattened to one row per asset (business terms and
field descriptions), with the term hierarchy carried in a `path` column and the
glossary metadata denormalized into each row.

Templates (`dbt-source`, `column-mapping`, etc.) only apply to system-side exports.
Glossary-side exports support `--format json|yaml|compact|csv` only.
