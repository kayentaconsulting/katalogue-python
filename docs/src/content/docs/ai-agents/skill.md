---
title: AI Agents
description: A ready-to-use skill for AI agents (Claude, Copilot, etc.) to answer any data catalog question using the Katalogue CLI.
---

AI agents can use the Katalogue CLI to answer natural-language questions about your
data catalog — from browsing systems and datasets to tracing business terms across
source systems, generating dbt sources, and auditing PII coverage.

This page provides a ready-made skill you can drop into your project so an AI agent
knows which commands to run and how to interpret the output.

## How to install the skill

Copy the skill below into your project as either:

**Option A — Claude Code skill** (recommended if you use Claude Code):

Create `.claude/skills/katalogue-cli/SKILL.md` in your project root and paste the content
below into it. Claude Code will load it automatically.

**Option B — CLAUDE.md or AGENTS.md**:

Paste the skill content into your project's `CLAUDE.md` or `AGENTS.md`. It works
alongside any existing instructions.

---

## The skill

````markdown
---
name: katalogue-cli
description: Use the Katalogue CLI to answer any data catalog question. Trigger whenever
  the user asks about systems, datasources, datasets, tables, columns, business terms,
  field descriptions, PII fields, dbt sources, column mappings, or schema exports —
  even if they don't mention "Katalogue" explicitly. Also trigger for requests like
  "what's in our data catalog", "find the schema for table X", "which fields are PII",
  "generate dbt sources", "where does business term X appear", or "build a datamart for Y".
---

# katalogue-cli

Use the Katalogue CLI to answer any data catalog question: browsing systems and
datasets, tracing business terms, auditing PII, generating dbt sources, and more.

## Authentication

Set these environment variables before running any command:

```
KATALOGUE_CLIENT_ID      (required)
KATALOGUE_CLIENT_SECRET  (required)
KATALOGUE_URL            (required — e.g. https://your-instance.katalogue.se)
```

If missing, pass `--client-id` / `--client-secret` / `--base-url` inline, or run
`katalogue auth login` to store credentials for the session.

## Data model

```
system
  └── datasource
        └── dataset_group
              └── dataset
                    └── field ──(field_description_id FK)──> field_description
                                                                     │
glossary                                                   (reference table, many-to-many)
  └── business_term ──────────────────────────────────────────────────┘
```

- Every `field` in any export response carries denormalized attributes —
  `field_description_name`, `is_pii`, `field_sensitivity_name`, `field_role_name` —
  no extra command needed.
- `field-description export` returns the linked business terms directly.
- `business-term export` returns the term → its field descriptions → the physical
  fields where each description appears (with full system/datasource/dataset context).
- `glossary export` returns the whole glossary as a recursive `business_terms` tree —
  each term nests its child terms and its `field_descriptions`. In CSV it flattens to
  one row per asset with a `path` column.

## Resources

| Resource | What it represents |
|---|---|
| `system` | Source system (CRM, DW, ERP, …) |
| `datasource` | Database or connection within a system |
| `dataset-group` | Schema or namespace within a datasource |
| `dataset` | Table or view |
| `field` | Column within a dataset |
| `glossary` | Collection of business terms |
| `business-term` | Named concept in a glossary |
| `field-description` | Reusable semantic description applied to fields |

## Commands

### list

All resources: `katalogue <resource> list [--<parent> <id>]`

| Resource | Parent flag |
|---|---|
| `system` | — |
| `datasource` | `--system <id>` |
| `dataset-group` | `--datasource <id>` |
| `dataset` | `--dataset-group <id>` |
| `field` | `--dataset <id>` |
| `glossary` | — |
| `business-term` | `--glossary <id>` |
| `field-description` | `--business-term <id>` or `--field <id>` |

Key flags: `--format <fmt>` · `--filter <expr>` · `--properties <a,b,c>` · `--wide`

### get

```bash
katalogue system get 1
katalogue datasource get 5 --include-children --format json
katalogue field-description get 167 --format json
```

`--include-children` returns the record and all descendants in one call. The response
is a flat canonical shape with each level in its own top-level list (`datasources`,
`datasets`, `fields`, …).

### export

`export` = `get --include-children` writing to a file (default: `<resource>-<id>.json`).

```bash
# System-side (support --template and --split-by)
katalogue datasource export 5 --template dbt-source
katalogue dataset-group export 12 --template column-mapping
katalogue dataset export 42 --format yaml

# Glossary-side (JSON/YAML/compact/CSV only — no templates)
katalogue glossary export 2 --format json          # recursive business_terms tree
katalogue glossary export 2 --format csv           # one row per asset, path column
katalogue business-term export 8 --format json
katalogue field-description export 167 --format json
```

File flags: `--output-file <path>` · `--output-dir <dir>` · `--split-by <level>` ·
`--filename-template '<expr>'` · `--overwrite` · `--dry-run`

### keys

```bash
katalogue field keys          # one name per line — use before --filter or --properties
katalogue dataset keys --format json
```

## Filtering

`<property> <op> <value>` — repeat `--filter` for AND:

```bash
katalogue field list --filter is_pii=true --filter datatype_category=string
katalogue dataset list --filter 'dataset_name contains order'
```

Operators: `=` `!=` `>` `<` `>=` `<=` `contains` `startswith` `endswith`

String operators are case-insensitive. Booleans: `true`/`false`.

**Hierarchical filters** scope to one level when used with `--include-children`:

```bash
katalogue system get 1 --include-children --filter field.is_pii=true
```

## Output formats

| Format | Notes |
|---|---|
| `json` | Default for `get`/`export`; use when parsing nested responses |
| `json-compact` / `compact` | Single-line JSON — preferred for agent list scanning |
| `yaml` / `yml` | Human-readable config output |
| `csv` | Flat; good for spreadsheets or `--output-file` |
| `table` | Default for `list`; TTY only — avoid in agent context |

## Templates (system-side only)

Applies to `system`, `datasource`, `dataset-group`, `dataset` exports.
Not available for `glossary`, `business-term`, or `field-description`.

| Template | Output |
|---|---|
| `dbt-source` | dbt v2 `sources.yml` |
| `column-mapping` | YAML column list |
| `json-template` | Full JSON hierarchy (use to inspect all available keys) |
| `nested-yml` | Indented YAML tree |
| `./path/to/template.j2` | Custom Jinja2 |

```bash
katalogue datasource export 5 --template dbt-source
katalogue datasource export 5 --template dbt-source \
  --split-by dataset --output-dir ./dbt/models \
  --filename-template '{{ dataset.dataset_name }}.yml'
```

## Datatype conversion

`--datatype-converter` maps source types to a target platform (system-side exports only).
Built-in: `sqlserver-to-databricks`, `db2-to-databricks`

```bash
katalogue datasource export 5 --template column-mapping --datatype-converter sqlserver-to-databricks
```

## Discovery workflow

Navigate top-down to find IDs. Skip steps you can infer from context.

**Step 1 — Find system and datasource**
```bash
katalogue system list --properties system_id,system_name --format json-compact
katalogue datasource list --system <id> --properties datasource_id,datasource_name --format json-compact
```

**Step 2 — List schemas and tables**
```bash
katalogue dataset-group list --datasource <id> --properties dataset_group_id,dataset_group_name --format json-compact
katalogue dataset list --dataset-group <id> --properties dataset_id,dataset_name --format json-compact
```

**Step 3 — Get columns**
```bash
katalogue field list --dataset <id> \
  --properties field_name,datatype_fullname,is_pii,field_description_name --format json
```

Shortcut — export the full system tree in one call instead of navigating step by step:
```bash
katalogue system export <id> --format json
```

## Common patterns

### "What datasets/tables are in system X?"

```bash
katalogue system list --format json-compact            # find system_id
katalogue datasource list --system <id> --format json-compact
katalogue dataset-group list --datasource <id> --format json-compact
katalogue dataset list --dataset-group <id> --format json-compact
```

### "What columns does table X have?"

```bash
katalogue dataset list --format json-compact           # find dataset_id
katalogue field list --dataset <id> --format json      # includes field_description_name, is_pii, datatype_fullname
```

### "Which fields are PII in datasource/system X?"

```bash
katalogue datasource get <id> --include-children --filter field.is_pii=true --format json
# as CSV:
katalogue system get <id> --include-children --filter field.is_pii=true --format csv \
  --output-file pii-inventory.csv
```

### "Generate dbt sources for datasource X"

```bash
katalogue datasource export <id> --template dbt-source
# one file per dataset:
katalogue datasource export <id> --template dbt-source --split-by dataset --output-dir ./dbt/models
```

### "Where does business term X appear in source systems?"

```bash
katalogue business-term list --format json-compact      # find term_id
katalogue business-term export <id> --format json
# Response: field_descriptions[].fields[] → each has system_name, datasource_name, dataset_name, field_name
```

### "What business term and glossary is field Y in dataset Z connected to?"

```bash
katalogue dataset export <dataset_id> --format json     # find field_description_id on the field
katalogue field-description export <fd_id> --format json
# Response: business_terms[{ business_term_name, glossary_name }], fields[...]
```

### "Build a datamart for business terms A, B, C"

```bash
katalogue business-term list --format json-compact      # find ids
katalogue business-term export <id_A> --format json     # collect dataset_ids from fields[]
katalogue business-term export <id_B> --format json
katalogue business-term export <id_C> --format json
# Deduplicate dataset_ids, then for each:
katalogue dataset export <dataset_id> --template dbt-source
```

### "What's the full structure of glossary X?" / "Export glossary X"

```bash
katalogue glossary list --format json-compact          # find glossary_id
katalogue glossary export <id> --format json
# Response: business_terms[] tree — each term has field_descriptions[] and nested business_terms[]
# For a spreadsheet: --format csv → one row per asset with a `path` column
```

### "What field descriptions are linked to business term X?"

```bash
katalogue business-term export <id> --format json
# field_descriptions[] → name, is_pii, field_role_name, and physical fields[]
```

### "Export column mapping for system X with type conversion"

```bash
katalogue system export <id> \
  --template column-mapping \
  --datatype-converter sqlserver-to-databricks \
  --split-by dataset --output-dir ./mappings
```

### "Full schema of datasource X as YAML"

```bash
katalogue datasource export <id> --template nested-yml
```

### "What keys/properties are available for resource X?"

```bash
katalogue field keys
# or export with json-template to see all keys in context:
katalogue dataset export <id> --template json-template
```

## Example agent workflows

### "What PII data is in our CRM system?"

```
agent: katalogue system list --format json-compact
  → finds system_id=3 for "CRM"

agent: katalogue system get 3 --include-children --filter field.is_pii=true --format json
  → returns all PII fields with their dataset, datasource, and type info
  → answers: "CRM has 12 PII fields across 4 datasets: customers.email,
    customers.phone, orders.billing_address, ..."
```

### "Generate dbt sources for our Snowflake datasource, one file per dataset"

```
agent: katalogue datasource list --format json-compact
  → finds datasource_id=7 for "Snowflake DW"

agent: katalogue datasource export 7 --template dbt-source \
         --split-by dataset --output-dir ./dbt/models
  → writes orders.yml, customers.yml, products.yml, ...
```

### "Which business term and glossary is `customer_id` in the `orders` table connected to?"

```
agent: katalogue dataset list --format json-compact
  → finds dataset_id=55 for "orders"

agent: katalogue dataset export 55 --format json
  → finds customer_id field, reads field_description_id=42

agent: katalogue field-description export 42 --format json
  → business_terms[0].business_term_name = "Customer ID"
  → business_terms[0].glossary_name = "Core Concepts"
```

### "Build a datamart for business terms Revenue, Customer ID, and Order Date"

```
agent: katalogue business-term list --format json-compact
  → finds ids: Revenue=12, Customer ID=7, Order Date=31

agent: katalogue business-term export 12 --format json   (Revenue)
agent: katalogue business-term export 7  --format json   (Customer ID)
agent: katalogue business-term export 31 --format json   (Order Date)
  → collects unique dataset_ids from fields[] across all three: 55, 22, 68

agent: katalogue dataset export 55 --template dbt-source
agent: katalogue dataset export 22 --template dbt-source
agent: katalogue dataset export 68 --template dbt-source
```

### "Write a dbt staging model for the `orders` table in production Postgres"

```
agent: katalogue system list --properties system_id,system_name --format json-compact
  → system_id=1, system_name="Production"

agent: katalogue datasource list --system 1 --properties datasource_id,datasource_name --format json-compact
  → datasource_id=3, datasource_name="production_postgres"

agent: katalogue dataset-group list --datasource 3 --properties dataset_group_id,dataset_group_name --format json-compact
  → dataset_group_id=11, dataset_group_name="public"

agent: katalogue dataset list --dataset-group 11 --filter 'dataset_name=orders' \
         --properties dataset_id,dataset_name,dataset_description --format json-compact
  → dataset_id=47, dataset_name="orders"

agent: katalogue field list --dataset 47 \
         --properties field_name,datatype_fullname,is_pii,field_description_name --format json
  → [{"field_name": "order_id", "datatype_fullname": "INTEGER", "is_pii": false, ...}, ...]
```

Now write `stg_orders.sql` and its schema YAML using the real column names, types, and PII flags.
````

---

## Related

- [CLI commands](/katalogue-python/cli/commands) — full command and flag reference
- [Output formats](/katalogue-python/cli/output-formats) — formats, file output, split-by
- [Exporting hierarchies](/katalogue-python/guides/exporting) — end-to-end export recipes
- [Templates](/katalogue-python/guides/templates) — built-in and custom Jinja2 templates
- [Filtering & selection](/katalogue-python/reference/filtering) — filter operators and dotted paths
- [Resources](/katalogue-python/reference/resources) — hierarchy, response shapes, default columns
