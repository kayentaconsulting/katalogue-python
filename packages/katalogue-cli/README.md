# katalogue-cli

CLI for [Katalogue](https://katalogue.se), based on the Katalogue REST API.

## Installation

```bash
pip install katalogue-cli
# or with uv
uv add katalogue-cli
```

Before the package is published to PyPI, install directly from GitHub. The CLI depends on `katalogue-sdk`, so both must be provided together:

```bash
# with uv
uv pip install \
  "git+https://github.com/kayentaconsulting/katalogue-cli.git#subdirectory=packages/katalogue-sdk" \
  "git+https://github.com/kayentaconsulting/katalogue-cli.git#subdirectory=packages/katalogue-cli"

# or with pip
pip install \
  "git+https://github.com/kayentaconsulting/katalogue-cli.git#subdirectory=packages/katalogue-sdk" \
  "git+https://github.com/kayentaconsulting/katalogue-cli.git#subdirectory=packages/katalogue-cli"
```

**For development:**

```bash
git clone <repo-url>
cd katalogue-cli
uv sync
```

Verify the install:

```bash
katalogue --version
```

## Configuration

The CLI authenticates using [OAuth2 client credentials from Katalogue](https://docs.katalogue.se/using-katalogue/katalogue_cli_and_sdk/#granting-access-to-katalogue). Set these environment variables (or pass them as flags):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `KATALOGUE_CLIENT_ID` | Yes | — | OAuth2 client ID |
| `KATALOGUE_CLIENT_SECRET` | Yes | — | OAuth2 client secret |
| `KATALOGUE_URL` | No | `https://your-instance.katalogue.se` | API base URL |
| `KATALOGUE_TOKEN_URL` | No | `https://your-instance.katalogue.se/oidc/token` | OAuth2 token endpoint |

**Precedence:** CLI flag > environment variable > default value.

OAuth2 scopes are derived automatically per operation (e.g. `system.read` for system commands).

## Resources

The hierarchy is: **system → datasource → dataset-group → dataset → field**

| Resource | Commands |
|----------|----------|
| `system` | `list`, `get`, `keys` |
| `datasource` | `list`, `get`, `keys` |
| `dataset-group` | `list`, `get`, `keys` |
| `dataset` | `list`, `get`, `keys` |
| `field` | `list`, `get`, `keys` |
| `glossary` | `list`, `get`, `keys` |

## Commands

### list

```bash
katalogue system list
katalogue field list --dataset <id>
katalogue datasource list --system <id>
katalogue dataset-group list --datasource <id>
katalogue dataset list --dataset-group <id>
```

### get

```bash
katalogue system get <id>
katalogue field get <id>
```

### keys

Discover available field names for use with `--filter` and `--fields`:

```bash
katalogue field keys              # one key per line
katalogue dataset keys --format json
```

The keys come from a live API call — they reflect what the API actually returns.

## Filtering and output

### --filter

Filter results by any column value. Repeat for AND logic:

```bash
katalogue field list --filter is_pii=true
katalogue field list --filter is_pii=true --filter field_type=TEXT
katalogue system list --filter system_type=Database
```

Supported operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `contains`, `startswith`, `endswith`.
String operators (`=`, `contains`, `startswith`, `endswith`) are case-insensitive.

```bash
katalogue system list --filter 'system_name contains CRM'
katalogue field list --filter 'field_name startswith user_'
```

All filtering happens client-side after the API fetch.

### --fields

Return only specific columns — useful for large responses or scripting:

```bash
katalogue system list --fields system_id,system_name
katalogue field list --fields field_name,is_pii --format json
```

### --format

Controls the serialization format of the output.

| Format | Output | Best for |
|--------|--------|----------|
| `table` | Human-readable table (default for `list`) | Interactive use |
| `json` | Pretty-printed JSON (default for `get`) | Scripting, piping to `jq` |
| `yaml` / `yml` | YAML | Config files, readability |
| `json-compact` / `compact` | Single-line JSON, no whitespace | Streaming, `grep` |
| `csv` | CSV, flattened to lowest level | Spreadsheets, data analysis |

```bash
katalogue system list --format table
katalogue system list --format json
katalogue system list --format yaml
katalogue field list --format csv
katalogue field list --format json-compact | grep '"is_pii":true'
```

When `--include-children` is used with `--format csv`, hierarchical data is flattened to the lowest available level (fields if present, otherwise datasets, dataset groups, or datasources). Parent values are repeated in every child row.

```bash
katalogue system get 1 --include-children --format csv
# -> one CSV row per field, with system/datasource/dataset columns denormalized into each row
```

### --template

Renders the result using a Jinja2 template. Templates control the structure and shape of the output independently of `--format`.

| Template | Output | Description |
|----------|--------|-------------|
| `dbt-source` | YAML | dbt `sources.yml` structure |
| `column-mapping` | YAML | Field-level column mapping |
| `json-template` | JSON | Full hierarchical context as JSON |
| `./path/to/file.j2` | depends | Custom Jinja2 template file |

```bash
# Built-in templates — use natural format (YAML or JSON)
katalogue datasource get 5 --include-children --template dbt-source
katalogue datasource get 5 --include-children --template column-mapping
katalogue datasource get 5 --include-children --template json-template

# Custom .j2 file
katalogue datasource get 5 --include-children --template ./my_template.j2
```

`--template` requires `--include-children` for hierarchical data (datasource, system, etc.).

### Combining --template and --format

Use `--format` alongside `--template` to convert the template's natural output to another serialization format:

```bash
# dbt-source renders YAML by default; convert to JSON
katalogue datasource get 5 --include-children --template dbt-source --format json

# Convert dbt-source YAML to compact JSON
katalogue datasource get 5 --include-children --template dbt-source --format json-compact

# json-template renders JSON by default; convert to YAML
katalogue datasource get 5 --include-children --template json-template --format yaml
```

`--format table` cannot be combined with `--template`.

## Hierarchical Retrieval

Use `--include-children` on any `get` command to fetch the resource and all its descendants in a single call:

```bash
katalogue system get 1 --include-children
katalogue datasource get 5 --include-children --format json
katalogue datasource get 5 --include-children --format yaml
```

### Writing output to files

Use `--output-file` to write the rendered output to a file instead of printing it:

```bash
# Write JSON to a file
katalogue system get 1 --include-children --format json --output-file ./export.json

# Write dbt-source YAML to a file
katalogue datasource get 5 --include-children --template dbt-source --output-file ./sources.yml

# Overwrite existing file
katalogue datasource get 5 --include-children --template dbt-source \
  --output-file ./sources.yml --overwrite
```

### Splitting output into multiple files

Use `--split-by` with `--output-dir` to write one file per resource level:

```bash
# One JSON file per dataset
katalogue system get 1 --include-children --format json \
  --split-by dataset --output-dir ./out/

# One dbt-source YAML file per dataset
katalogue system get 1 --include-children --template dbt-source \
  --split-by dataset --output-dir ./dbt/models/

# One file per datasource, converted to JSON
katalogue system get 1 --include-children --template dbt-source --format json \
  --split-by datasource --output-dir ./out/
```

Valid `--split-by` levels depend on the root resource:

| Root resource | Valid split levels |
|---------------|--------------------|
| `system` | `system`, `datasource`, `dataset_group`, `dataset` |
| `datasource` | `datasource`, `dataset_group`, `dataset` |
| `dataset_group` | `dataset_group`, `dataset` |
| `dataset` | `dataset` |

**File extensions** are derived automatically: `--format yaml` → `.yaml`, `--format json` → `.json`, `--format csv` → `.csv`, `--template dbt-source` → `.yml`, `--template json-template` → `.json`, custom `.j2` file → `.yml`.

### Custom filename template

```bash
katalogue system get 1 --include-children --template dbt-source \
  --split-by dataset --output-dir ./out \
  --filename-template '{{ dataset.dataset_name }}.yml'
```

### Dry run

Preview planned files without writing them:

```bash
katalogue system get 1 --include-children --template dbt-source \
  --split-by dataset --output-dir ./out --dry-run
```

## Global flags

| Flag | Env var | Description |
|------|---------|-------------|
| `--client-id` | `KATALOGUE_CLIENT_ID` | OAuth2 client ID |
| `--client-secret` | `KATALOGUE_CLIENT_SECRET` | OAuth2 client secret |
| `--base-url` | `KATALOGUE_URL` | API base URL |
| `--token-url` | `KATALOGUE_TOKEN_URL` | OAuth2 token endpoint |
| `--verbose` / `-v` | — | Show HTTP request details on stderr |
| `--version` | — | Show version and exit |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | API error, auth error, or missing configuration |
| 2 | CLI usage error (bad arguments) |

## Development

```bash
uv sync           # install dependencies
uv run pytest     # run all tests
uv run katalogue --help
```
