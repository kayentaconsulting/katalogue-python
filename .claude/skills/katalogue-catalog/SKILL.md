---
name: katalogue-catalog
description: Use this skill whenever you need to explore the data catalog to understand what data sources, schemas, tables, or columns exist — especially before writing dbt models, SQL transformations, data pipelines, or any code that references real table or column names. Trigger this skill when the user asks to model data, build transformations, write queries against catalog sources, generate dbt sources or staging models, understand schema structure, find PII fields, or document tables. Don't try to guess table or column names — use this skill to look them up first.
---

# Katalogue Catalog Explorer

Use this skill to discover the real schema, tables, and columns in the data catalog before writing any transformation logic. Looking things up takes seconds and prevents hallucinated column names.

## Credentials

The CLI authenticates with OAuth2 client credentials. Check for these env vars before running any commands:

```
KATALOGUE_CLIENT_ID      (required)
KATALOGUE_CLIENT_SECRET  (required)
KATALOGUE_URL            (optional, defaults to https://demo-api.katalogue.se)
```

If missing, ask the user to set them or pass `--client-id` / `--client-secret` flags directly.

---

## Resource Hierarchy

```
system
  └─ datasource          (a database connection, e.g. "production_postgres")
       └─ dataset_group  (a schema, e.g. "public", "raw", "analytics")
            └─ dataset   (a table or view, e.g. "orders", "customers")
                 └─ field (a column, with name, type, description, is_pii)

glossary                 (independent — business term definitions)
```

---

## Complete Command Reference

Every valid command at a glance:

| Resource       | Commands           | Parent filter flag       |
|----------------|--------------------|--------------------------|
| `system`       | `list` `get` `keys` | —                       |
| `datasource`   | `list` `get` `keys` | `--system <id>`         |
| `dataset-group`| `list` `get` `keys` | `--datasource <id>`     |
| `dataset`      | `list` `get` `keys` | `--dataset-group <id>`  |
| `field`        | `list` `get` `keys` | `--dataset <id>`        |
| `glossary`     | `list` `get` `keys` | —                       |
| `export`       | `system <id>` `glossary <id>` | —            |

All `list` commands accept `--fields`, `--where`, and `--format`. All `get` commands accept `--fields` and `--format`.

---

## Discovery Workflow

### Step 0 — Orient: list systems (skip if you already know the datasource)

```bash
katalogue system list --fields system_id,system_name
```

You need a `system_id` to use `--system` filters or `export system`. If the catalog has only one system, this is a one-time lookup.

---

### Step 1 — Find the datasource

```bash
katalogue datasource list --fields datasource_id,datasource_name,datasource_type_name
```

If you know the system it belongs to:
```bash
katalogue datasource list --system <system_id> --fields datasource_id,datasource_name
```

Pick the right datasource and note its `datasource_id`.

---

### Step 2 — List schemas (dataset groups)

```bash
katalogue dataset-group list --datasource <datasource_id> --fields dataset_group_id,dataset_group_name,description
```

Note the `dataset_group_id` for the schema you care about.

---

### Step 3 — List tables in a schema

```bash
katalogue dataset list --dataset-group <dataset_group_id> \
  --fields dataset_id,dataset_name,dataset_type,description
```

`dataset_type` is typically `TABLE` or `VIEW`. Note the `dataset_id` for tables you need to model.

---

### Step 4 — Get columns for a table

```bash
katalogue field list --dataset <dataset_id> \
  --fields field_name,field_type,is_pii,description
```

This gives you everything needed to write a transformation: column names, types, PII flags, and descriptions.

---

### Step 5 — Discover available field names (when unsure what's filterable)

Before using `--where` or `--fields`, check what the API actually returns:

```bash
katalogue field keys        # one key per line
katalogue dataset keys
katalogue dataset-group keys
katalogue system keys
katalogue glossary keys
```

---

## `--where` Syntax

Filter list results by field value. The flag is repeatable — multiple `--where` clauses are ANDed together.

```bash
# Single condition
katalogue field list --dataset <id> --where is_pii=true

# Multiple conditions (AND)
katalogue field list --dataset <id> --where is_pii=true --where field_type=VARCHAR

# String match
katalogue dataset list --dataset-group <id> --where dataset_name=orders
```

**Type coercion** (automatic):
- `true` / `false` → boolean
- Pure integer string → integer
- Anything else → string (no quotes needed)

Use the `keys` command for a resource first if you're unsure which field names are available.

---

## Common Patterns

### Get all tables and columns in a schema at once

```bash
# 1. Get all tables
katalogue dataset list --dataset-group <id> --fields dataset_id,dataset_name,dataset_type,description

# 2. For each dataset_id, get columns
katalogue field list --dataset <id> --fields field_name,field_type,is_pii,description
```

Loop across all dataset IDs from step 1 to build a complete column inventory.

---

### Find all PII columns (for masking or exclusion)

```bash
katalogue field list --dataset <id> --where is_pii=true --fields field_name,description
```

Across an entire schema:
```bash
# Get all dataset IDs first, then for each:
katalogue field list --dataset <id> --where is_pii=true --fields field_name
```

---

### Look up a specific table by name

```bash
katalogue dataset list --dataset-group <id> --where dataset_name=orders
```

---

### Fetch a single resource by ID

When you already have an ID and need its full details without listing:

```bash
katalogue system get <system_id>
katalogue datasource get <datasource_id>
katalogue dataset-group get <dataset_group_id>
katalogue dataset get <dataset_id>
katalogue field get <field_id>
```

---

### Get a rich column list for dbt model documentation

```bash
katalogue field list --dataset <id> --fields field_name,description,is_pii
```

Pipe into your dbt YAML template — `field_name` → column name, `description` → column description, `is_pii=true` → add `meta: {pii: true}`.

---

### Get a full system tree in one shot

When you need broad discovery across an entire system (all datasources, schemas, tables, and fields), skip the step-by-step traversal and export the full tree:

```bash
katalogue export system <system_id>
```

Returns a nested JSON document with everything. Useful as a first pass before drilling into specific tables.

---

### Explore the business glossary

The glossary is independent of the system hierarchy and contains business term definitions. Useful for mapping terms to column descriptions or validating dbt docs against business language.

```bash
# List all glossaries
katalogue glossary list --fields glossary_id,glossary_name

# Get a single glossary's metadata
katalogue glossary get <glossary_id>

# Export a full glossary with all terms and definitions
katalogue export glossary <glossary_id>
```

---

## Output Tips

- **Default format is JSON** — good for programmatic use. Parse with `json.loads()` or `jq`.
- Use `--fields` to scope output to only the keys you need — reduces noise.
- Use `--format table` for a quick human-readable overview.
- Use `--format compact` for NDJSON (one JSON object per line) — efficient for piping large result sets to `jq` or processing line-by-line in scripts.
- Exit code `0` = success, `1` = API/auth error, `2` = bad arguments.

---

## Worked Example

> "I need to write a dbt staging model for the `orders` table in the production Postgres."

```bash
# 0. Find the system (if needed)
katalogue system list --fields system_id,system_name
# → system_id: 1, system_name: Production

# 1. Find the datasource
katalogue datasource list --system 1 --fields datasource_id,datasource_name
# → datasource_id: 3, datasource_name: production_postgres

# 2. Find the schema
katalogue dataset-group list --datasource 3 --fields dataset_group_id,dataset_group_name
# → dataset_group_id: 11, dataset_group_name: public

# 3. Find the table
katalogue dataset list --dataset-group 11 --where dataset_name=orders --fields dataset_id,dataset_name,description
# → dataset_id: 47, dataset_name: orders, description: "Customer order records"

# 4. Get all columns
katalogue field list --dataset 47 --fields field_name,field_type,is_pii,description
# → [{"field_name": "order_id", "field_type": "INTEGER", ...}, ...]
```

Now you have everything needed to write `stg_orders.sql` and its schema YAML.
