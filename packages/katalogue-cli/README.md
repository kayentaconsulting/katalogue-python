# katalogue-cli

CLI for [Katalogue](https://katalogue.se), based on the Katalogue REST API.

## Installation

**From git (no PyPI required):**

```bash
pip install git+https://github.com/your-org/katalogue-cli.git
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
| `KATALOGUE_URL` | No | `https://demo-api.katalogue.se` | API base URL |
| `KATALOGUE_TOKEN_URL` | No | `https://demo-api.katalogue.se/oidc/token` | OAuth2 token endpoint |

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

**Precedence:** CLI flag > environment variable > default value.

OAuth2 scopes are derived automatically per operation (e.g. `system.read` for system commands).

## Resources

The hierarchy is: **system → datasource → dataset-group → dataset → field**

| Resource | Commands |
|----------|----------|
| `system` | `list`, `get`, `children`, `keys` |
| `datasource` | `list`, `get`, `children`, `keys` |
| `dataset-group` | `list`, `get`, `children`, `keys` |
| `dataset` | `list`, `get`, `children`, `keys` |
| `field` | `list`, `get`, `keys` |
| `glossary` | `list`, `get`, `keys` |

## Commands

### list

```bash
katalogue system list
katalogue field list --dataset <id>
katalogue datasource list --system <id>
```

### get

```bash
katalogue system get <id>
katalogue field get <id>
```

### children

Navigate one level down the hierarchy without knowing the child resource name:

```bash
katalogue system children <id>         # lists datasources
katalogue datasource children <id>     # lists dataset-groups
katalogue dataset-group children <id>  # lists datasets
katalogue dataset children <id>        # lists fields
```

### keys

Discover available field names for use with `--where` and `--fields`:

```bash
katalogue field keys              # one key per line
katalogue dataset keys --format json
```

The keys come from a live API call — they reflect what the API actually returns.

## Filtering and output

### --where

Filter results by any column value. Repeat for AND logic:

```bash
katalogue field list --where is_pii=true
katalogue field list --where is_pii=true --where field_type=TEXT
katalogue system list --where system_type=Database
```

Values are coerced automatically: `true`/`false` → bool, digit strings → int, everything else → string.

Use `keys` to find filterable column names:

```bash
katalogue field keys
# field_id
# field_name
# field_type
# is_pii
# ...
katalogue field list --where field_type=TEXT
```

### --fields

Return only specific columns — useful for large responses or scripting:

```bash
katalogue system list --fields system_id,system_name
katalogue field list --fields field_name,is_pii --format json
```

### --format

| Format | Output | Best for |
|--------|--------|----------|
| `json` | Pretty-printed JSON (default) | Scripting, piping to `jq` |
| `table` | Human-readable table | Interactive use |
| `compact` | One JSON object per line | Streaming, `grep` |

```bash
katalogue system list --format table
katalogue field list --format compact | grep '"is_pii": true'
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

See `PROJECT_PLAN.md` for architecture details and roadmap.
