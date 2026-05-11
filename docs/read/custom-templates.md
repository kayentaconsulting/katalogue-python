# Writing custom templates

Katalogue uses [Jinja2](https://jinja.palletsprojects.com/) for templating. When you pass `--template ./my_template.j2` (or a repo-registered name), the template receives a context dict describing the catalog hierarchy at the requested scope.

## Template context variables

All variables are always present in the context dict. Single-resource variables (`system`, `datasource`, `dataset_group`, `dataset`, `glossary`) are `None` or an empty dict `{}` when not applicable for the current scope — use the `| default('', true)` filter to guard against this.

| Variable | Type | Description |
|---|---|---|
| `resource` | `str` | Root resource type: `"system"`, `"datasource"`, `"dataset_group"`, or `"dataset"` |
| `system` | `dict` | System metadata, or `{}` if not in scope |
| `datasource` | `dict` | Single datasource, or `{}` when multiple datasources are in scope |
| `datasources` | `list[dict]` | All datasources in scope |
| `dataset_group` | `dict` | Single dataset group, or `{}` when multiple are in scope |
| `dataset_groups` | `list[dict]` | All dataset groups in scope |
| `dataset` | `dict` | Single dataset, or `{}` when multiple are in scope |
| `datasets` | `list[dict]` | All datasets in scope |
| `fields` | `list[dict]` | Fields scoped to the current context (filtered per split level) |
| `glossary` | `dict` | Glossary metadata, or `{}` when not in scope |
| `terms` | `list[dict]` | Glossary terms |

### How context shifts with `--split-by`

Without `--split-by`, one file is rendered with the full hierarchy. With `--split-by`, the pipeline renders one file per resource at the chosen level, and the context is scoped accordingly:

| `--split-by` | `datasource` | `dataset_group` | `dataset` | `fields` |
|---|---|---|---|---|
| `datasource` | single dict | all groups for this datasource | all datasets for this datasource | all fields for this datasource |
| `dataset_group` | single dict | single dict | all datasets for this group | all fields for this group |
| `dataset` | single dict | single dict | single dict | fields for this dataset only |

## Common field keys

Fields are API objects — the available keys depend on your Katalogue instance configuration, but the built-in templates use these:

| Key | Description |
|---|---|
| `field_name` | Column/field name |
| `dataset_name` | Name of the parent dataset |
| `dataset_id` | ID of the parent dataset |
| `datatype_fullname` | Full data type string (preferred) |
| `field_datatype` | Fallback data type string |
| `field_source_description` | Description from the source system (preferred) |
| `description` | Fallback description |
| `is_pii` | Boolean — field contains PII (preferred) |
| `field_is_pii` | Fallback PII flag |
| `field_is_primary_key` | Boolean — field is a primary key |

To discover all available keys for your data, render using the built-in `json-template`:

```bash
katalogue datasource get 5 --include-children --template json-template
```

## Jinja2 environment

- **Sandboxed** — access to Python builtins and unsafe attributes is blocked.
- **StrictUndefined** — referencing a variable that is not defined raises a `TemplateUndefinedError`. Always use `| default('', true)` for keys that may be absent, e.g. `{{ f.field_source_description | default('', true) }}`.
- Standard Jinja2 filters are available: `default`, `lower`, `upper`, `tojson`, `selectattr`, `list`, `first`, `join`, `string`, etc.

## Template registry

Repo-local templates are registered in a config file so they can be referenced by name instead of path. Katalogue searches for the registry by walking up from the current working directory to the git root and stopping at the first config file found.

### Discovery order

For each directory from `cwd` up to the git root:

1. `katalogue.toml` — checked first
2. `pyproject.toml` — used if no `katalogue.toml` is found in that directory

The first file that contains a `[templates]` section wins. `katalogue.toml` always takes precedence over `pyproject.toml` within the same directory.

### Registration syntax

**`katalogue.toml`:**

```toml
[templates.<name>]
path = "relative/path/to/template.j2"
default_format = "yml"
```

**`pyproject.toml`:**

```toml
[tool.katalogue.templates.<name>]
path = "relative/path/to/template.j2"
default_format = "yml"
```

`path` is resolved relative to the config file's directory. It must end in `.j2`.

`default_format` sets the file extension used when writing output with `--output-file` or `--split-by`. Any non-empty string is valid (`yml`, `json`, `csv`, `md`, `txt`, etc.). Defaults to `yml`. Format conversion (e.g. `--format json`) is only supported when `default_format` is `yml`, `yaml`, or `json`.

### Overriding built-in templates

If a repo registers a name that matches a built-in (`dbt-source`, `column-mapping`, `json-template`), the repo version wins. This lets you customise built-in templates per project without changing the package.

### Using a direct path

Templates can also be referenced by path without registration:

```bash
katalogue datasource get 5 --include-children --template ./templates/catalog-md.j2
```

Unregistered `.j2` paths default to `yml` as the output format.

## Example: minimal custom template

Templates can produce any text format. Here is a Markdown template that renders a dataset dictionary:

```jinja2
# {{ datasource.datasource_name | default(system.system_name | default('Catalog', true), true) }}

{% for ds in datasets %}
## {{ ds.dataset_name }}

{{ ds.dataset_description | default('', true) }}

| Column | Type | PII |
|--------|------|-----|
{% for f in fields if f.dataset_id == ds.dataset_id %}
| `{{ f.field_name }}` | {{ f.datatype_fullname | default(f.field_datatype | default('', true), true) }} | {{ f.is_pii | default(f.field_is_pii | default(false, true), true) | string | lower }} |
{% endfor %}

{% endfor %}
```

Save as `templates/catalog-md.j2` and register it:

```toml
# katalogue.toml
[templates.catalog-markdown]
path = "templates/catalog-md.j2"
default_format = "md"
```

```toml
# pyproject.toml
[tool.katalogue.templates.catalog-markdown]
path = "templates/catalog-md.j2"
default_format = "md"
```

Then run:

```bash
katalogue datasource get 5 --include-children --template catalog-markdown
```

## Filename templates

When using `--split-by` with `--output-dir`, you can control per-file names with `--filename-template`. The expression is a Jinja2 expression (not a full template file) evaluated against the same context:

```bash
katalogue datasource get 5 --include-children \
  --template dbt-source \
  --split-by dataset_group \
  --output-dir ./sources \
  --filename-template "{{ dataset_group.dataset_group_name }}_sources.yml"
```
