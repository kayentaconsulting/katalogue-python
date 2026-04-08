# CLI Reference

## Overview

`katalogue` is a command-line interface for the Katalogue Data Catalog API. It lets you browse and query the data catalog hierarchy from your terminal or from scripts and AI agents.

## Data Model

The catalog is organized as a strict hierarchy:

```
system
  └── datasource
        └── dataset_group
              └── dataset
```

| Level | What it represents | Example |
|-------|--------------------|---------|
| **system** | A software system or platform that owns data | `Kayenta Apps`, `Katalogue` |
| **datasource** | A database or storage layer within a system | `kayenta_apps` (PostgreSQL) |
| **dataset_group** | A schema or logical grouping of tables | `feedback`, `core`, `stage` |
| **dataset** | A single table or view | `questionnaire`, `response` |

Each level can be listed independently or filtered by its parent, which lets you navigate the hierarchy step by step.

---

## Authentication

The CLI uses OAuth2 client credentials. Set these environment variables (or use a `.env` file in your working directory):

```
KATALOGUE_CLIENT_ID=your-client-id
KATALOGUE_CLIENT_SECRET=your-client-secret
KATALOGUE_TOKEN_URL=https://demo-api.katalogue.se/oidc/token   # optional, has default
KATALOGUE_URL=https://demo-api.katalogue.se                    # optional, has default
```

OAuth2 scopes are derived automatically per command (e.g. `system.read`, `datasource.read`). You don't set them manually.

---

## Global Options

These flags apply to every command and must be placed **before** the resource name:

```
katalogue [OPTIONS] <resource> <command> [args]
```

| Flag | Env var | Description |
|------|---------|-------------|
| `--client-id TEXT` | `KATALOGUE_CLIENT_ID` | OAuth2 client ID |
| `--client-secret TEXT` | `KATALOGUE_CLIENT_SECRET` | OAuth2 client secret |
| `--base-url TEXT` | `KATALOGUE_URL` | API base URL |
| `--token-url TEXT` | `KATALOGUE_TOKEN_URL` | OAuth2 token endpoint |
| `-v, --verbose` | — | Print request details to stderr |

---

## Output Formats

Every `list` and `get` command accepts `--format`:

| Value | Description | Best for |
|-------|-------------|----------|
| `json` | Pretty-printed JSON (default) | Scripts, piping, AI agents |
| `table` | Column-aligned human-readable table | Interactive use |

```bash
katalogue system list --format table
katalogue system list --format json | jq '.[0]'
```

---

## Commands

### `system`

The top of the hierarchy. A system represents a software platform that owns data.

```bash
# List all systems
katalogue system list [--format json|table]

# Get a system by ID
katalogue system get <id> [--format json|table]
```

**Examples:**

```bash
katalogue system list --format table

katalogue system get 1
katalogue system get 1 --format table
```

---

### `datasource`

A datasource is a database or storage layer belonging to a system.

```bash
# List all datasources
katalogue datasource list [--format json|table]

# List datasources for a specific system
katalogue datasource list --system <system_id> [--format json|table]

# Get a datasource by ID
katalogue datasource get <id> [--format json|table]
```

**Examples:**

```bash
# All datasources across the catalog
katalogue datasource list

# Datasources for Kayenta Apps (system 10)
katalogue datasource list --system 10 --format table

katalogue datasource get 10
```

---

### `dataset-group`

A dataset group is a schema or logical grouping of datasets within a datasource (e.g. a PostgreSQL schema).

```bash
# List all dataset groups
katalogue dataset-group list [--format json|table]

# List dataset groups for a specific datasource
katalogue dataset-group list --datasource <datasource_id> [--format json|table]

# Get a dataset group by ID
katalogue dataset-group get <id> [--format json|table]
```

**Examples:**

```bash
# Schemas inside datasource 10 (kayenta_apps)
katalogue dataset-group list --datasource 10 --format table

katalogue dataset-group get 25
```

---

### `dataset`

A dataset is a single table or view within a dataset group.

```bash
# List all datasets
katalogue dataset list [--format json|table]

# List datasets for a specific dataset group
katalogue dataset list --dataset-group <dataset_group_id> [--format json|table]

# Get a dataset by ID
katalogue dataset get <id> [--format json|table]
```

**Examples:**

```bash
# Tables in the feedback schema (dataset group 25)
katalogue dataset list --dataset-group 25 --format table

katalogue dataset get 459
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | API error, authentication failure, or missing configuration |
| `2` | CLI usage error (bad arguments or flags) |

---

## Example Workflows

### Discover the catalog top-down

Start from all systems, pick one, and drill down to its datasets:

```bash
# 1. See all systems
katalogue system list --format table

# 2. Pick a system (e.g. Kayenta Apps = ID 10), see its datasources
katalogue datasource list --system 10 --format table

# 3. Pick a datasource (e.g. kayenta_apps = ID 10), see its schemas
katalogue dataset-group list --datasource 10 --format table

# 4. Pick a schema (e.g. feedback = ID 25), see its tables
katalogue dataset list --dataset-group 25 --format table

# 5. Inspect a specific table
katalogue dataset get 459
```

### Look up a known resource by ID

```bash
katalogue system get 1
katalogue datasource get 10
katalogue dataset-group get 25
katalogue dataset get 459
```

### Pipe into jq for scripting

```bash
# Get the name of every dataset in a schema
katalogue dataset list --dataset-group 25 --format json \
  | jq -r '.datasets[].dataset_name'

# Find all tables (not views)
katalogue dataset list --dataset-group 25 --format json \
  | jq '[.datasets[] | select(.dataset_type_name == "Table")]'

# Get IDs and names of all systems
katalogue system list --format json \
  | jq -r '.systems[] | "\(.system_id)\t\(.system_name)"'
```

### Use in a shell script

```bash
#!/usr/bin/env bash
SYSTEM_ID=10
DATASOURCE_ID=$(
  katalogue datasource list --system "$SYSTEM_ID" --format json \
    | jq -r '.datasources[0].datasource_id'
)
echo "First datasource ID: $DATASOURCE_ID"

katalogue dataset-group list --datasource "$DATASOURCE_ID" --format json \
  | jq -r '.dataset_groups[].dataset_group_name'
```

---

## Notes

- **Response wrappers**: List responses are wrapped in a resource-named key (e.g. `{"systems": [...]}`, `{"datasets": [...]}`). When piping to `jq`, use `.systems[]`, `.datasets[]`, etc.
- **IDs**: All IDs are integers. Use the `list` commands to discover them.
- **Verbose mode**: Add `-v` before the resource name to see the HTTP request details on stderr, which is useful for debugging.

```bash
katalogue -v datasource list --system 10
```
