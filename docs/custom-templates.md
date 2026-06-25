# Writing custom templates

Katalogue uses [Jinja2](https://jinja.palletsprojects.com/) for templating. Every `katalogue <resource> export` command can render its output through a template — built-in (`dbt-source`, `nested-yml`, `column-mapping`, `json-template`) or your own `.j2` file.

## Contents

- [Quick start](#quick-start)
- [How the catalog looks in templates](#how-the-catalog-looks-in-templates)
- [Recipes](#recipes)
  - [Markdown data dictionary](#markdown-data-dictionary)
  - [Nested-YAML fields](#nested-yaml-fields)
  - [dbt-source skeleton](#dbt-source-skeleton)
  - [Dotted-column CSV](#dotted-column-csv)
- [Registering and using templates](#registering-and-using-templates)
- [Reference](#reference)
  - [Context variables](#context-variables)
  - [Common field keys](#common-field-keys)
  - [Built-in helpers](#built-in-helpers)
  - [Jinja2 environment](#jinja2-environment)
  - [User-defined macros](#user-defined-macros)
  - [Filename templates](#filename-templates)

---

## Quick start

Run a built-in template against any dataset and look at the result:

```bash
katalogue dataset export 99 --template nested-yml
# wrote ./dataset-99.yml
cat dataset-99.yml
```

The output is YAML describing the full in-scope hierarchy. Ancestors of the resource you exported are walked from `system` down to the dataset, and each dataset's fields are rendered with nested objects (`STRUCT`/`RECORD`/`ARRAY`) as indented sub-fields:

```yaml
system: ProdCatalog
datasources:
  - name: SalesDB
    dataset_groups:
      - name: public
        datasets:
          - name: events
            fields:
            - name: timestamp
              data_type: TIMESTAMP
            - name: payload
              data_type: STRUCT
              fields:
              - name: user_id
                data_type: STRING
              - name: location
                data_type: STRUCT
                fields:
                - name: city
                  data_type: STRING
```

The same template works at every scope (`system`, `datasource`, `dataset_group`, `dataset` export) — higher-scope exports produce more siblings at each level; narrower exports produce a 1-item chain down to the leaf.

Want a different shape? Skip to [Recipes](#recipes) and copy one of the four starter templates.

---

## How the catalog looks in templates

When a template renders, it receives a single context dict describing everything in scope. Two things are worth understanding before writing your own template.

### The context shape

```
context
├─ system          (single dict)
├─ datasource      (single dict, when one is in scope)
├─ datasources     (list, when many are in scope)
├─ dataset_group   (single dict, when one is in scope)
├─ dataset_groups  (list)
├─ dataset         (single dict)
├─ datasets        (list)
├─ fields          (flat list — see below)
├─ glossary        (single dict)
└─ terms           (list)
```

Which variables are "single" vs. "list" depends on the scope of your command. `dataset export <id>` puts one dataset in `dataset` and many in `datasets: [that one dataset]`; `datasource export <id>` puts many datasets in `datasets`. The full table is in the [Reference](#context-variables).

### Why `fields` is flat — and how `fields_tree` un-flattens it

A dataset's `fields` are always a single flat list, even when some are nested inside structs/objects/arrays. Nesting is expressed by `parent_field_id`:

```json
[
  {"field_id": 1, "parent_field_id": null, "field_name": "timestamp"},
  {"field_id": 2, "parent_field_id": null, "field_name": "payload"},
  {"field_id": 3, "parent_field_id": 2,    "field_name": "user_id"},
  {"field_id": 4, "parent_field_id": 2,    "field_name": "location"},
  {"field_id": 5, "parent_field_id": 4,    "field_name": "city"}
]
```

Walking that flat list with `parent_field_id` lookups is painful in Jinja2. The built-in helper **`fields_tree(dataset_id)`** does it for you — it returns a nested list with `.children` already attached:

```
flat list:                   fields_tree(dataset_id) returns:

f1 timestamp                 timestamp           (children: [])
f2 payload         ─┐        payload             (children: [user_id, location])
f3 user_id  ◀──────┤         ├─ user_id         (children: [])
f4 location ◀──────┤         └─ location        (children: [city])
f5 city     ◀──── (f4)          └─ city         (children: [])
```

Each node in the tree also carries a `field_path` (`"payload.location.city"`) — handy for flat dbt-style output. With `fields_tree` in hand, walking nested fields is a `{% for ... recursive %}` loop with no macros. Every recipe below uses it.

---

## Recipes

Copy-paste any of these, save next to your code, register, and run. Each is a complete template.

### Markdown data dictionary

One row per field per dataset. Useful for human-readable docs.

```jinja2
# {{ datasource.datasource_name | default(system.system_name | default('Catalog', true), true) }}

{% for ds in datasets %}
## {{ ds.dataset_name }}

{{ dataset_desc(ds) }}

| Column | Type | PII |
|--------|------|-----|
{% for f in fields_tree(ds.dataset_id) %}
| `{{ f.field_name }}` | {{ field_type(f) }} | {{ field_is_pii(f) | string | lower }} |
{% endfor %}

{% endfor %}
```

Save as `templates/catalog-md.j2`, register as `catalog-markdown`, then:

```bash
katalogue datasource export 5 --template catalog-markdown
```

### Nested-YAML fields

A minimal indented-YAML pattern — one `dataset:` block per dataset, fields nested below. Good as a teaching example for the `recursive` loop. The built-in `nested-yml` template uses the same `recursive` + `loop.depth0` pattern but wraps it in the full `datasources → dataset_groups → datasets → fields` chain so it works at every scope; see `nested_yml.j2` in the package source for the full version.

```jinja2
{% for ds in datasets %}
dataset: {{ ds.dataset_name }}
fields:
{% for f in fields_tree(ds.dataset_id) recursive %}    {# 1 #}
{{ '  ' * loop.depth0 }}- name: {{ f.field_name }}    {# 2 #}
{{ '  ' * loop.depth0 }}  data_type: {{ field_type(f) }}
{% if field_desc(f) %}
{{ '  ' * loop.depth0 }}  description: {{ field_desc(f) | yaml_str }}
{% endif %}
{% if f.children %}
{{ '  ' * loop.depth0 }}  fields:
{{ loop(f.children) -}}                                {# 3 #}
{% endif %}
{%- endfor %}
{%- endfor %}
```

How it works:

1. `recursive` on the `{% for %}` tells Jinja2 the loop body can re-enter itself.
2. `loop.depth0` is the current recursion depth (0 for roots, 1 for first-level children, etc.) — multiply by `'  '` to indent.
3. `{{ loop(f.children) -}}` re-runs the loop body for this field's children at the next depth. The trailing `-` strips the newline that would otherwise produce a blank line between siblings.

When you need indentation under an outer parent (e.g. fields nested *inside* `datasets: - name: X`), add a base offset: `{{ '  ' * (loop.depth0 + N) }}` where `N` is the depth of the outer scope. Keep the `{{ ... }}` expression flush against column 0 — Jinja's `lstrip_blocks` only strips before `{% %}` tags, not before output expressions.

### dbt-source skeleton

Flat list of columns with dotted names for nested fields (`payload.location.city`). The `field_path` attribute on each tree node already encodes the dotted path, so the recursion stays simple.

```jinja2
version: 2
sources:
  - name: {{ dataset_group.dataset_group_name }}
    tables:
{% for ds in datasets %}
      - name: {{ ds.dataset_name }}
        columns:
{% for f in fields_tree(ds.dataset_id) recursive %}
          - name: {{ f.field_path }}
            data_type: {{ field_type(f) }}
            description: {{ field_desc(f) | yaml_str }}
{{ loop(f.children) -}}
{%- endfor %}
{% endfor %}
```

Save as `templates/dbt-source-min.j2`. For the full version (datasource lookup across multiple groups, `config.meta` for PII/primary key flags), see `dbt_source.j2` in the package — it's the same pattern with a few extra lines.

```bash
katalogue dataset-group export 12 --template dbt-source-min
```

### Dotted-column CSV

Single line per column, with dotted paths. The simplest possible use of `fields_tree`.

```jinja2
dataset,column,type
{% for ds in datasets %}
{% for f in fields_tree(ds.dataset_id) recursive %}
{{ ds.dataset_name }},{{ f.field_path }},{{ field_type(f) }}
{{ loop(f.children) -}}
{% endfor %}
{% endfor %}
```

Output looks like:

```
dataset,column,type
events,timestamp,TIMESTAMP
events,payload,STRUCT
events,payload.user_id,STRING
events,payload.location,STRUCT
events,payload.location.city,STRING
```

Save as `templates/columns.csv.j2`, register with `default_format = "csv"`, run:

```bash
katalogue datasource export 5 --template columns-csv
```

---

## Registering and using templates

Templates can be referenced by **name** (registered in a config file) or by **path** to a `.j2` file. Katalogue looks for the registry by walking up from `cwd` to the git root, picking the first config file found.

### `katalogue.toml`

```toml
[templates.catalog-markdown]
path = "templates/catalog-md.j2"
default_format = "md"

[templates.columns-csv]
path = "templates/columns.csv.j2"
default_format = "csv"
```

### `pyproject.toml`

```toml
[tool.katalogue.templates.catalog-markdown]
path = "templates/catalog-md.j2"
default_format = "md"
```

- `path` is resolved relative to the config file's directory; it must end in `.j2`.
- `default_format` sets the file extension when writing output. Any non-empty string is valid (`yml`, `json`, `csv`, `md`, `txt`, …). Defaults to `yml`.
- Format conversion (e.g. `--format json`) is only supported when `default_format` is `yml`, `yaml`, or `json`.
- If a repo registers a name that matches a built-in, **the repo version wins** — useful for project-specific overrides.

### Direct path (no registration)

```bash
katalogue datasource export 5 --template ./templates/catalog-md.j2
```

Unregistered `.j2` paths default to `yml` as the output format.

---

## Reference

### Context variables

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

#### How context shifts with `--split-by`

Without `--split-by`, one file is rendered with the full hierarchy. With `--split-by`, the pipeline renders one file per resource at the chosen level, and the context is scoped accordingly:

| `--split-by` | `datasource` | `dataset_group` | `dataset` | `fields` |
|---|---|---|---|---|
| `datasource` | single dict | all groups for this datasource | all datasets for this datasource | all fields for this datasource |
| `dataset_group` | single dict | single dict | all datasets for this group | all fields for this group |
| `dataset` | single dict | single dict | single dict | fields for this dataset only |

### Common field keys

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
| `datatype_converted` | Target platform type string — present only when `--datatype-converter` is set |

To discover every key on your data, render with the built-in `json-template`:

```bash
katalogue datasource export 5 --template json-template
```

### Built-in helpers

Templates have access to a small set of domain helpers that absorb the most common boilerplate — fallback chains for partial field metadata and the flat-to-nested reshape for `parent_field_id` trees.

| Helper | Returns | Replaces |
|---|---|---|
| `field_type(f)` | `f.datatype_converted` → `f.datatype_fullname` → `f.field_datatype` → `''` | Triple `default(...)` chain |
| `field_desc(f)` | `f.field_source_description` → `f.description` → `''` | Description fallback |
| `field_is_pii(f)` | `True` if `is_pii` or `field_is_pii` is set | PII flag fallback |
| `field_is_primary_key(f)` | `True` if `field_is_primary_key` is set | PK flag fallback |
| `dataset_desc(ds)` | `ds.dataset_description` → `ds.description` → `''` | Dataset description fallback |
| `fields_tree(dataset_id=None)` | List of root field dicts with `children` and `field_path` attached recursively | Manual `selectattr` + recursive macros |
| `\| yaml_str` | *(filter)* Encodes any value as a valid YAML scalar — plain for simple strings, double-quoted with `\n` escapes for multiline, PyYAML-quoted for special characters, `''` for empty | Manual quoting / escaping in templates |

`fields_tree` builds a nested view of the flat `fields` list using `parent_field_id`. With `dataset_id` it returns roots for that dataset only; with no argument it returns roots across all datasets in scope. Each node carries two derived keys:

- `children` — list of child field dicts (already nested), empty for leaves
- `field_path` — dotted path from the root, e.g. `"address.city"` (useful for dbt-style flat column lists)

Orphans (children whose parent isn't in the pool) are promoted to roots so they aren't silently dropped.

### Jinja2 environment

- **Sandboxed** — access to Python builtins and unsafe attributes is blocked.
- **StrictUndefined** — referencing a variable that is not defined raises a `TemplateUndefinedError`. Always use `| default('', true)` for keys that may be absent, e.g. `{{ f.field_source_description | default('', true) }}`.
- **`trim_blocks=True` and `lstrip_blocks=True`** — block tags (`{% ... %}`) on their own line consume the newline that follows. To avoid blank lines between sibling iterations, add a leading `-` to the closing tag (`{%- endfor %}`) which strips trailing whitespace from the loop body:

  ```jinja2
  {% for child in f.children %}
  {{ loop(f.children) -}}
  {%- endfor %}
  ```

- Standard Jinja2 filters are available: `default`, `lower`, `upper`, `tojson`, `selectattr`, `list`, `first`, `join`, `string`, etc.

### User-defined macros

You can write your own macro files and import them into custom templates. Two discovery mechanisms are supported.

#### Template-relative import (automatic)

Place a macro file next to your template file. It is automatically available for import with no configuration:

```
templates/
  catalog.j2          # your template
  my_macros.j2        # your macro file — importable automatically
```

```jinja2
{# catalog.j2 #}
{% from 'my_macros.j2' import format_type %}
...
```

#### Project-registered macro paths

To share macros across multiple templates that live in different directories, register a macro search path:

**`katalogue.toml`:**

```toml
[macro_paths]
paths = ["macros/", "shared/templates/"]
```

**`pyproject.toml`:**

```toml
[tool.katalogue.macro_paths]
paths = ["macros/", "shared/templates/"]
```

Paths are resolved relative to the config file's directory.

#### Macro import search order

When a template contains `{% from 'file.j2' import ... %}`, Katalogue searches these locations in order — first match wins:

1. **Template's own directory** — resolved only when a `.j2` path was passed to `--template`
2. **Registered project macro paths** — from `[macro_paths]` in `katalogue.toml` or `pyproject.toml`

### Filename templates

When using `--split-by` with `--output-dir`, you can control per-file names with `--filename-template`. The expression is a Jinja2 expression (not a full template file) evaluated against the same context:

```bash
katalogue datasource export 5 \
  --template dbt-source \
  --split-by dataset_group \
  --output-dir ./sources \
  --filename-template "{{ dataset_group.dataset_group_name }}_sources.yml"
```
