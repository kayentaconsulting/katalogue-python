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
```

You almost always start at **datasource** and work down.

---

## Discovery Workflow

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
katalogue datasource children <datasource_id>
```

Or equivalently:
```bash
katalogue dataset-group list --datasource <datasource_id> --fields dataset_group_id,dataset_group_name,description
```

Note the `dataset_group_id` for the schema you care about.

---

### Step 3 — List tables in a schema

```bash
katalogue dataset-group children <dataset_group_id>
```

Or with explicit fields:
```bash
katalogue dataset list --dataset-group <dataset_group_id> \
  --fields dataset_id,dataset_name,dataset_type,description
```

`dataset_type` is typically `TABLE` or `VIEW`. Note the `dataset_id` for tables you need to model.

---

### Step 4 — Get columns for a table

```bash
katalogue dataset children <dataset_id>
```

Or scoped:
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
```

---

## Common Patterns for Data Modeling

### Get all tables and columns in a schema at once

When you need a full picture of a schema to start modeling:

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

### Get a rich column list for dbt model documentation

```bash
katalogue field list --dataset <id> --fields field_name,description,is_pii
```

Pipe into your dbt YAML template — `field_name` → column name, `description` → column description, `is_pii=true` → add `meta: {pii: true}`.

---

### Generate a dbt sources.yml (if the generate command is available)

```bash
katalogue generate dbt-sources --datasource-id <id>
katalogue generate dbt-sources --datasource-id <id> --dataset-group-id <id>
katalogue generate dbt-sources --datasource-id <id> --split --output ./models/sources/
```

---

## Output Tips

- **Default format is JSON** — good for programmatic use. Parse with `json.loads()` or `jq`.
- Use `--fields` to scope output to only the keys you need — reduces noise.
- Use `--format table` if you want a quick human-readable overview.
- Exit code `0` = success, `1` = API/auth error, `2` = bad arguments.

---

## Worked Example

> "I need to write a dbt staging model for the `orders` table in the production Postgres."

```bash
# 1. Find the datasource
katalogue datasource list --fields datasource_id,datasource_name
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
