# Output formats and file output

The CLI separates **what** the data looks like (`--format`), **how** it is shaped
(`--template`), and **where** it goes (stdout, a file, or many files). This page
covers formats and file output; templating has its own [guide](../guides/templates.md).

## Contents

- [Serialization formats](#serialization-formats)
- [CSV and hierarchical data](#csv-and-hierarchical-data)
- [Writing output to a file](#writing-output-to-a-file)
- [Splitting output into multiple files](#splitting-output-into-multiple-files)
- [Custom filenames](#custom-filenames)
- [Dry run](#dry-run)

## Serialization formats

Set with `--format` / `-f`.

| Format | Output | Best for |
|--------|--------|----------|
| `table` | Human-readable table (default for `list`) | Interactive use |
| `json` | Pretty-printed JSON (default for `get`) | Scripting, piping to `jq` |
| `yaml` / `yml` | YAML | Config files, readability |
| `json-compact` / `compact` | Single-line JSON, no whitespace | Streaming, `grep` |
| `csv` | CSV, flattened to the lowest level | Spreadsheets, data analysis |

```bash
katalogue system list --format table
katalogue system list --format json
katalogue system list --format yaml
katalogue field list --format csv
katalogue field list --format json-compact | grep '"is_pii":true'
```

`table` is for display only: it cannot be combined with `--template` or any
file-output option, and the `export` command does not accept it (its choices are
`json`, `yaml`, `yml`, `json-compact`, `compact`, `csv`).

## CSV and hierarchical data

When `--include-children` is combined with `--format csv`, the hierarchy is
flattened to the lowest available level (fields if present, otherwise datasets,
dataset groups, or datasources). Parent values are repeated in every child row.

```bash
katalogue system get 1 --include-children --format csv
# → one CSV row per field, with system/datasource/dataset columns denormalized into each row
```

## Writing output to a file

Use `--output-file` / `-o` to write rendered output to a file instead of printing it.

```bash
# Write JSON to a file
katalogue system get 1 --include-children --format json --output-file ./export.json

# Write dbt-source YAML to a file
katalogue datasource export 5 --template dbt-source --output-file ./sources.yml

# Overwrite an existing file
katalogue datasource export 5 --template dbt-source --output-file ./sources.yml --overwrite
```

## Splitting output into multiple files

Use `--split-by` / `-s` with `--output-dir` / `-d` to write one file per resource level.

```bash
# One JSON file per dataset
katalogue system get 1 --include-children --format json \
  --split-by dataset --output-dir ./out/

# One dbt-source YAML file per dataset
katalogue system export 1 --template dbt-source \
  --split-by dataset --output-dir ./dbt/models/
```

Valid `--split-by` levels depend on the root resource:

| Root resource | Valid split levels |
|---------------|--------------------|
| `system` | `system`, `datasource`, `dataset_group`, `dataset` |
| `datasource` | `datasource`, `dataset_group`, `dataset` |
| `dataset_group` | `dataset_group`, `dataset` |
| `dataset` | `dataset` |

**File extensions** are derived automatically: `--format yaml` → `.yaml`,
`--format json` → `.json`, `--format csv` → `.csv`; built-in or repo-registered
templates use their configured default format; and direct `.j2` files fall back to
`.yml`. When both a format and a template are set, the format wins.

## Custom filenames

With `--split-by`, control per-file names using `--filename-template` — a Jinja2
expression evaluated against each split's context:

```bash
katalogue system export 1 --template dbt-source \
  --split-by dataset --output-dir ./out \
  --filename-template '{{ dataset.dataset_name }}.yml'
```

See [Filename templates](../guides/templates.md#filename-templates) for the available
context variables.

## Dry run

Preview the planned files without writing anything:

```bash
katalogue system export 1 --template dbt-source \
  --split-by dataset --output-dir ./out --dry-run
```

The output lists every file that *would* be created.
