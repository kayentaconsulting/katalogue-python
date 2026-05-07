# Writing Custom Jinja2 Templates

Custom templates let you render Katalogue data in any text format — YAML, SQL, Markdown, JSON, or anything else. Pass them with `--template ./your-template.j2`.

## Jinja2 environment

The SDK uses a **sandboxed Jinja2 environment** with two important settings enabled:

| Setting | Effect |
|---------|--------|
| `trim_blocks=True` | The first newline after a block tag (`{% ... %}`) is automatically removed |
| `lstrip_blocks=True` | Leading whitespace before a block tag on its own line is automatically stripped |
| `StrictUndefined` | Accessing an undefined variable raises an error (no silent empty strings) |

**What this means in practice:** you do not need whitespace control characters (`-`) in your templates. Control tags on their own lines produce no blank lines in the output.

## Whitespace: the key rule

With `trim_blocks` and `lstrip_blocks` enabled, put control tags on their own lines — the environment handles the whitespace for you. Do **not** add `-` to `{%` or `%}`.

**Correct** — clean output, no stray blank lines:

```jinja2
columns:
{% for f in fields %}
  - name: {{ f.field_name }}
    type: {{ f.field_datatype }}
{% if f.is_pii %}
    meta:
      pii: true
{% endif %}
{% endfor %}
```

**Broken** — `-%}` fights `trim_blocks` and eats the newline that belongs to the next content line:

```jinja2
columns:
{% for f in fields %}
  - name: {{ f.field_name }}
    type: {{ f.field_datatype }}
{% if f.is_pii -%}
    meta:
      pii: true
{% endif -%}
{% endfor %}
```

The second version causes `meta:` and `pii:` to merge with the lines above them because `-%}` strips the trailing newline that `trim_blocks` would have handled cleanly.

**Rule:** write your templates as if `-%}` and `{%-` don't exist. They're only needed when these flags are *not* enabled.

## StrictUndefined and optional fields

`StrictUndefined` means any variable not in the context raises a `UndefinedError`. Use the `| default(...)` filter for optional fields:

```jinja2
{# Will raise an error if field_description is not in the data #}
{{ f.field_description }}

{# Safe — returns empty string if missing #}
{{ f.field_description | default('') }}

{# Chained defaults — try description, fall back to source_description, then '' #}
{{ f.description | default(f.field_source_description | default('')) }}
```

## Available context variables

All templates receive the full hierarchical context for the resource being rendered. The exact variables present depend on the root resource (`--include-children` is required for hierarchical data).

### System export context

```
resource          string — always "system"
system            dict   — system fields (system_id, system_name, ...)
datasources       list   — datasource dicts
dataset_groups    list   — dataset_group dicts (all, across all datasources)
datasets          list   — dataset dicts (all, across all dataset_groups)
fields            list   — field dicts (all, across all datasets)
```

### Datasource export context

```
resource          string — "datasource"
datasource        dict   — datasource fields
dataset_groups    list   — dataset_group dicts
datasets          list   — dataset dicts
fields            list   — field dicts
```

### Dataset-group / dataset export context

```
resource          string — "dataset_group" or "dataset"
dataset_group     dict   — (if dataset_group level)
dataset           dict   — (if dataset level)
datasets          list   — datasets under this group (if applicable)
fields            list   — fields under this context
```

### Glossary export context

```
resource          string — "glossary"
glossary          dict   — glossary fields
terms             list   — term dicts
```

### Split context

When using `--split-by`, each template render receives the slice for one resource at the split level, with its full ancestry included. For example, `--split-by dataset` gives each template call:

```
resource          "datasource" (root resource)
datasource        dict — the root datasource
dataset_group     dict — the parent dataset_group for this dataset
dataset           dict — the specific dataset for this split
fields            list — only the fields for this dataset
```

### Filename template context

`--filename-template '{{ dataset.dataset_name }}.yml'` receives the same split context as the content template.

## Worked example

A minimal template that generates a SQL `CREATE TABLE` statement:

```jinja2
-- Generated from Katalogue: {{ dataset.dataset_name }}
CREATE TABLE {{ dataset.dataset_name }} (
{% for f in fields %}
  {{ f.field_name }} {{ f.field_datatype | default('TEXT') }}{% if not loop.last %},{% endif %}

{% endfor %}
);
```

Save as `create_table.j2` and run:

```bash
katalogue dataset get 42 --include-children --template ./create_table.j2
```

## Registering templates

Instead of always passing the `.j2` file path, register templates in `katalogue.toml` or `pyproject.toml`:

```toml
# katalogue.toml
[templates.create-table]
path = "templates/create_table.j2"
default_format = "sql"
```

Then use by name:

```bash
katalogue dataset get 42 --include-children --template create-table
```

Registered templates with the same name as a built-in template take precedence.

## Built-in templates

The following templates are included and can be used as reference implementations:

| Name | Format | Description |
|------|--------|-------------|
| `dbt-source` | YAML | dbt `sources.yml` with columns and metadata |
| `column-mapping` | YAML | Field-level column mapping |
| `json-template` | JSON | Full hierarchical context serialized as JSON |

Source files: `packages/katalogue-sdk/src/katalogue/templates/`
