---
title: Filtering, selection, and sorting
description: Filter expressions, operators, dotted paths, property selection, and sort syntax.
---

Filtering, property selection, and sorting are the same concepts whether you use the
CLI (`--filter`, `--properties`) or the SDK (`GetOptions`). All of it happens
**client-side**, after the API fetch.

## Contents

- [Filter expressions](#filter-expressions)
- [Operators](#operators)
- [Dotted paths and hierarchical filters](#dotted-paths-and-hierarchical-filters)
- [Property selection](#property-selection)
- [Sorting (SDK)](#sorting-sdk)
- [Discovering field names](#discovering-field-names)

## Filter expressions

A filter is `path OP value`. Multiple filters are combined with AND.

CLI — repeat `--filter` / `-w`:

```bash
katalogue field list --filter is_pii=true
katalogue field list --filter is_pii=true --filter field_type=TEXT
katalogue system list --filter 'system_name contains CRM'
```

SDK — pass a list of strings (or `Filter` objects) to `GetOptions(filters=...)`:

```python
client.get("field", GetOptions(filters=["is_pii=true"]))
client.get("field", GetOptions(filters=["is_pii=true", 'datatype_fullname="varchar"']))
```

## Operators

| Operator | Meaning |
|----------|---------|
| `=` | Equals |
| `!=` | Not equals |
| `>` `<` `>=` `<=` | Numeric / ordinal comparison |
| `contains` | Substring match |
| `startswith` | Prefix match |
| `endswith` | Suffix match |

String operators (`=`, `contains`, `startswith`, `endswith`) are **case-insensitive**.
Boolean values are matched tolerantly: `true` and `false` match both the JSON boolean
form and any casing of the string form (`"true"`, `"True"`, `"TRUE"`).

```bash
katalogue field list --filter 'field_name startswith user_'
```

## Dotted paths and hierarchical filters

When fetching a hierarchy (`--include-children` / `include_children=True`), a dotted
path scopes the filter to one level. Only records at that level are pruned; ancestors
are retained.

```python
client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    filters=["field.is_pii=true"],   # keep only PII fields, keep their parents
))
```

```bash
katalogue system get 1 --include-children --filter field.is_pii=true
```

## Property selection

Return only specific properties — useful for large responses or scripting.

```bash
katalogue system list --properties system_id,system_name
katalogue field list --properties field_name,is_pii --format json
```

```python
client.get("system", GetOptions(properties=["system_id", "system_name"]))
```

In CLI `table` output, each resource has a default set of columns; pass `--wide` to
show all properties, or `--properties` to choose your own. See
[Resources](/katalogue-python/reference/resources) for the default columns per resource.

## Sorting (SDK)

Multi-column sort via `GetOptions(sort=...)`. `"asc"` / `"desc"` are case-insensitive;
null values always sort last.

```python
client.get("system", GetOptions(sort=[{"system_name": "asc"}]))
client.get("field", GetOptions(sort=[{"dataset_name": "asc"}, {"field_name": "asc"}]))
```

## Discovering field names

Filter and property names are the keys the API returns for your instance. Discover
them with the `keys` command (CLI) or by inspecting `result.data` (SDK):

```bash
katalogue field keys                 # one key per line
katalogue dataset keys --format json
```

See [Resources](/katalogue-python/reference/resources) for the commonly used keys on each resource.
