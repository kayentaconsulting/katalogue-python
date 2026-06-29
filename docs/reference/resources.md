# Resources reference

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

```
system
  └── datasource
        └── dataset_group
              └── dataset
                    └── field
glossary   (independent — no parent)
```

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
| `datatype_converted` | Target-platform type — present only when a [datatype converter](../guides/datatype-conversion.md) is active |
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

`include_children` returns a flat canonical shape — each child level in its own
top-level list, regardless of the root resource:

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

This is the same context that [templates](../guides/templates.md) receive when
rendering. Fields are a flat list linked by `parent_field_id`; the `fields_tree`
template helper reshapes them into a nested tree.
