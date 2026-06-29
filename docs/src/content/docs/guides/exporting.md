---
title: Exporting hierarchies
description: End-to-end recipes for include-children, split-by, and templated exports.
---

The most common real-world task is pulling a resource together with all its children
and writing the result somewhere useful — a JSON snapshot, a set of dbt source files,
a column mapping. This guide walks through that end-to-end with both the CLI and SDK.

It builds on [output formats](../cli/output-formats.md), [templates](templates.md),
and [SDK options](../sdk/options.md).

## Contents

- [Fetch a hierarchy](#fetch-a-hierarchy)
- [Write a single file](#write-a-single-file)
- [Split into one file per resource](#split-into-one-file-per-resource)
- [Recipe: dbt sources, one file per dataset](#recipe-dbt-sources-one-file-per-dataset)
- [Recipe: column mapping with type conversion](#recipe-column-mapping-with-type-conversion)
- [Recipe: PII inventory as CSV](#recipe-pii-inventory-as-csv)
- [Preview before writing](#preview-before-writing)

## Fetch a hierarchy

`--include-children` (CLI) / `include_children=True` (SDK) fetches a resource and all
descendants in one call. `export` is the CLI shorthand that always includes children
and writes to a file.

```bash
katalogue system get 1 --include-children --format json     # print
katalogue system export 1                                   # write system-1.json
```

```python
result = client.get("system", GetOptions(resource_id=1, include_children=True))
result.data["datasets"]   # flat list of all datasets under system 1
```

See [Resources](../reference/resources.md#hierarchical-response-shape) for the
returned shape.

## Write a single file

```bash
katalogue datasource export 5 --template dbt-source --output-file ./sources.yml
katalogue system get 1 --include-children --format json --output-file ./export.json --overwrite
```

```python
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(template="dbt-source", output_file="./sources.yml"),
))
print(result.output_file)  # "./sources.yml"
```

## Split into one file per resource

Use `--split-by` (CLI) / `split_by=` (SDK) with an output directory to write one file
per resource at the chosen level. Valid levels depend on the root resource — see
[Output formats](../cli/output-formats.md#splitting-output-into-multiple-files).

```bash
katalogue system export 1 --template dbt-source \
  --split-by dataset --output-dir ./dbt/models/
```

```python
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(template="dbt-source", split_by="dataset", output_dir="./dbt/models"),
))
for f in result.output_files:
    print(f.path)   # ./dbt/models/customers.yml, ./dbt/models/orders.yml, ...
```

## Recipe: dbt sources, one file per dataset

Generate a dbt `sources.yml` per dataset, named after the dataset:

```bash
katalogue system export 1 \
  --template dbt-source \
  --split-by dataset \
  --output-dir ./dbt/models \
  --filename-template '{{ dataset.dataset_name }}.yml'
```

## Recipe: column mapping with type conversion

Render a column mapping with source types converted to Databricks SQL:

```bash
katalogue datasource export 5 \
  --template column-mapping \
  --datatype-converter sqlserver-to-databricks
```

```python
result = client.get("datasource", GetOptions(
    resource_id=5,
    include_children=True,
    datatype_converter="sqlserver-to-databricks",
    output=OutputOptions(template="column-mapping"),
))
print(result.output)
```

See [Datatype conversion](datatype-conversion.md) for the full converter list and how
to register your own.

## Recipe: PII inventory as CSV

Flatten every PII field under a system into a spreadsheet-ready CSV. With
`--include-children`, CSV flattens to field level and denormalizes parent columns
into each row.

```bash
katalogue system get 1 --include-children \
  --filter field.is_pii=true \
  --format csv --output-file ./pii-inventory.csv
```

## Preview before writing

Add `--dry-run` (CLI) / `dry_run=True` (SDK) to see the planned files without
touching disk:

```bash
katalogue system export 1 --template dbt-source \
  --split-by dataset --output-dir ./out --dry-run
```

The output lists every file that would be created.
