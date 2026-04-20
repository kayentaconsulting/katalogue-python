# katalogue-sdk

Python client for [Katalogue](https://katalogue.se), based on the Katalogue REST API. 

## Installation

```bash
pip install katalogue-sdk
# or with uv
uv add katalogue-sdk
```

Before the package is published to PyPI, install directly from GitHub:

```bash
# with uv
uv pip install "git+https://github.com/kayentaconsulting/katalogue-cli.git#subdirectory=packages/katalogue-sdk"

# or with pip
pip install "git+https://github.com/kayentaconsulting/katalogue-cli.git#subdirectory=packages/katalogue-sdk"
```

## Quick Start

```python
from katalogue import KatalogueClient

client = KatalogueClient()  # reads KATALOGUE_CLIENT_ID / KATALOGUE_CLIENT_SECRET from env

# List all systems (Python object)
client.get("system")

# List systems — selected fields, sorted, as JSON
client.get("system", fields=["system_id", "system_name"], sort=[{"system_name": "asc"}], format="json")

# Single record by ID
client.get("system", resource_id=1)

# All datasources under a system
client.get("datasource", parent_id=1)

# All PII fields in a specific datasource — filtered client-side
client.get("field", filter={"datasource_id": 1, "is_pii": True}, fields=["field_id", "field_name", "dataset_name"])
```

## Credentials

### Get Katalogue Credentials
[Create an OAuth2 client](https://docs.katalogue.se/using-katalogue/katalogue_cli_and_sdk/#granting-access-to-katalogue) in Katalogue to get the client credentials referred to in the following section.

### Production — Azure Key Vault (recommended)

Fetch credentials from Key Vault at startup using `DefaultAzureCredential` (works with Managed Identity, workload identity, or local `az login`). Never store the secret in the environment or in code.

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from katalogue import KatalogueClient, resolve_settings

vault = SecretClient(
    vault_url="https://your-vault.vault.azure.net",
    credential=DefaultAzureCredential(),
)
settings = resolve_settings(
    client_id=vault.get_secret("katalogue-client-id").value,
    client_secret=vault.get_secret("katalogue-client-secret").value,
    base_url="https://your-instance.katalogue.se",    # or read from vault / app config
)
client = KatalogueClient(settings)
```

Dependencies:
```bash
uv add katalogue-sdk azure-identity azure-keyvault-secrets
```

`DefaultAzureCredential` resolves identity in this order: Managed Identity → Workload Identity → Azure CLI → Visual Studio Code. In Azure-hosted services (Functions, Container Apps, AKS) this means zero credentials in the app — just assign the Managed Identity read access to the vault.

### CI/CD pipelines

Inject secrets as environment variables from your pipeline's secret store (GitHub Actions secrets, Azure DevOps variable groups, etc.). The SDK picks them up automatically:

```bash
KATALOGUE_CLIENT_ID=...
KATALOGUE_CLIENT_SECRET=...
KATALOGUE_URL=https://your-instance.katalogue.se       # optional
KATALOGUE_TOKEN_URL=https://your-instance.katalogue.se/oidc/token  # optional
```

```python
from katalogue import KatalogueClient

client = KatalogueClient()   # reads env vars
```

### Local development

Use a `.env` file (never commit it). Load it before constructing the client:

```bash
# .env
KATALOGUE_CLIENT_ID=your-client-id
KATALOGUE_CLIENT_SECRET=your-client-secret
KATALOGUE_URL=https://your-instance.katalogue.se     
KATALOGUE_TOKEN_URL=https://your-instance.katalogue.se/oidc/token  
```

```python
from dotenv import load_dotenv
from katalogue import KatalogueClient

load_dotenv()
client = KatalogueClient()
```

`Settings` is a frozen Pydantic model. `client_secret` is stored as `SecretStr` and never appears in `repr()` or logs.

## Resource Hierarchy

Resources form a hierarchy. Pass these strings as the `resource` argument:

```
system
  └── datasource
        └── dataset_group
              └── dataset
                    └── field
glossary   (independent)
```

## `get()` — High-Level API

`get()` is the recommended way to query resources. It handles routing, filtering, sorting, and formatting in one call.

```python
client.get(
    resource,                        # required: "system", "datasource", "dataset_group", "dataset", "field", "glossary"
    resource_id=None,                # fetch a single record by ID
    parent_id=None,                  # fetch all children of this parent
    filter=None,                     # AND-logic key/value filter applied client-side
    fields=None,                     # keep only these fields in the result
    sort=None,                       # multi-column sort: [{"field": "asc"}, {"other": "desc"}]
    format=None,                     # "json" | "compact" | None (Python object, default)
    format_descriptions_as_text=False,  # convert rich-text description fields to plain text
)
```

### Routing

| `resource_id` | `parent_id` | Behaviour |
|---|---|---|
| — | — | All records of the resource type |
| ✓ | — | Single record by ID |
| — | ✓ | All children of that parent |
| ✓ | ✓ | Single record, `None` if it doesn't belong to the parent |

`parent_id` is silently ignored for top-level resources (`system`, `glossary`).

### List all records

```python
client.get("system", fields=["system_id", "system_name", "system_type"])
# -> [{"system_id": 1, "system_name": "Katalogue", "system_type": "Data Catalog"}, ...]
```

### Single record

```python
client.get("system", resource_id=1)
# -> {"system_id": 1, "system_name": "Katalogue", ...}
```

### Children by parent

Walk the full hierarchy: system → datasource → dataset_group → dataset → field.

```python
datasources = client.get("datasource", parent_id=1, fields=["datasource_id", "datasource_name"])

dataset_groups = client.get("dataset_group", parent_id=datasources[0]["datasource_id"],
                            fields=["dataset_group_id", "dataset_group_name"])

datasets = client.get("dataset", parent_id=dataset_groups[0]["dataset_group_id"],
                      fields=["dataset_id", "dataset_name"])

fields = client.get("field", parent_id=datasets[0]["dataset_id"],
                    fields=["field_id", "field_name", "data_type", "is_pii"])
```

### Scoped lookup

Returns `None` if the record doesn't belong to the given parent.

```python
client.get("field", resource_id=42, parent_id=10)
# -> record if field 42 is in dataset 10, else None
```

### Filter

AND-logic, applied client-side. Works on any field present in the API response.

```python
# All PII fields in a specific datasource
client.get("field",
    filter={"datasource_id": 1, "is_pii": True},
    fields=["field_id", "field_name", "dataset_name", "datasource_name", "is_pii"])
```

### Sort

Multi-column. `"asc"` and `"desc"` are case-insensitive. Null values always sort last.

```python
client.get("system", sort=[{"system_name": "asc"}], fields=["system_id", "system_name"])

# Multi-column: primary key first
client.get("field", sort=[{"dataset_name": "asc"}, {"field_name": "asc"}])
```

### Output format

```python
client.get("system", fields=["system_id", "system_name"])          # Python object (default)
client.get("system", fields=["system_id", "system_name"], format="json")     # pretty JSON string
client.get("system", fields=["system_id", "system_name"], format="compact")  # minified JSON string
```

### Plain-text descriptions

Description fields are stored as rich-text JSON. Pass `format_descriptions_as_text=True` to extract plain text.

```python
client.get("system",
    fields=["system_id", "system_name", "system_description"],
    format_descriptions_as_text=True)
# -> [{"system_id": 1, "system_name": "Katalogue", "system_description": "User-friendly system..."}]
```

### Validation

`resource`, `format`, and sort `direction` are validated. Invalid values raise `ValueError` with the list of accepted values.

```python
client.get("ssystem")
# ValueError: Invalid resource 'ssystem'. Must be one of: dataset, dataset_group, datasource, field, glossary, system

client.get("system", format="table")
# ValueError: Invalid format 'table'. Must be one of: compact, json

client.get("system", sort=[{"system_name": "ascending"}])
# ValueError: Invalid sort direction 'ascending' for column 'system_name'. Must be 'asc' or 'desc'.
```

## Utilities

These functions are available directly from `katalogue` for use outside of `get()`.

### `filter_fields(data, fields)`

Keep only the requested fields from a dict or list of dicts. Wrapper dicts (e.g. `{"systems": [...]}`) are unwrapped automatically.

```python
from katalogue import filter_fields

filter_fields([{"id": 1, "name": "A", "extra": "x"}], ["id", "name"])
# -> [{"id": 1, "name": "A"}]

filter_fields({"id": 1, "name": "A", "extra": "x"}, ["id", "name"])
# -> {"id": 1, "name": "A"}

filter_fields(data, None)   # fields=None — data returned unchanged
filter_fields(data, [])     # fields=[] — data returned unchanged
```

### `filter_resultset(data, key, value)`

Keep only rows where `row[key] == value`. Unwraps wrapper dicts automatically.

```python
from katalogue import filter_resultset

rows = [{"type": "db", "name": "Orders"}, {"type": "api", "name": "Events"}]
filter_resultset(rows, "type", "db")
# -> [{"type": "db", "name": "Orders"}]
```

### `sort_resultset(data, sort)`

Sort a list of dicts by one or more columns. Null values are always sorted last regardless of direction.

```python
from katalogue import sort_resultset

rows = [{"name": "Charlie"}, {"name": "Alice"}, {"name": "Bob"}]

sort_resultset(rows, [{"name": "asc"}])
# -> [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]

# Multi-column: primary sort first in the list
sort_resultset(rows, [{"type": "asc"}, {"name": "desc"}])

sort_resultset(rows, None)   # None — data returned unchanged
```

### `format_descriptions_to_plaintext(data)`

Recursively converts rich-text description fields (stored as JSON strings) to plain text. Strings that are not rich-text JSON are returned unchanged. Works on a single string, a dict, or a list of dicts.

```python
from katalogue import format_descriptions_to_plaintext

format_descriptions_to_plaintext("just a plain string")
# -> "just a plain string"

format_descriptions_to_plaintext(None)
# -> None

# Applied recursively to all string values in a list of records
records = [{"name": "A", "description": "<rich-text-json>"}]
format_descriptions_to_plaintext(records)
# -> [{"name": "A", "description": "plain text extracted from blocks"}]
```

### `format_resultset(data, fmt)`

Route a result to a string formatter. Used internally by `get(format=...)`.

```python
from katalogue import format_resultset

format_resultset(data, "json")     # -> pretty-printed JSON string
format_resultset(data, "compact")  # -> compact JSON string, no spaces
format_resultset(data, None)       # -> data unchanged (Python object)
```

### `format_json(data)` / `format_compact_json(data)`

Direct JSON formatters.

```python
from katalogue import format_json, format_compact_json

format_json([{"id": 1}])         # -> '[\n  {\n    "id": 1\n  }\n]'
format_compact_json([{"id": 1}]) # -> '[{"id":1}]'
```

## Low-Level Client Methods

These are available for advanced use cases where you need direct control over API calls.

```python
# List all records of a resource type (returns raw API envelope)
client.list_resource("system")
# -> {"systems": [{"system_id": 1, ...}, ...]}

# Get a single record by ID
client.get_resource("system", 1)
# -> {"system_id": 1, "system_name": "Katalogue", ...}

# List children of a parent resource
client.list_by_parent("datasource", "system", 1)
# -> [{"datasource_id": 1, ...}, ...]

# Full system export (all nested data in one call)
client.get_system_export(1)
# -> {"meta": {...}, "data": {"system": {...}, "datasources": [...], ...}}

# Full glossary export
client.get_glossary_export(1)
# -> {"meta": {...}, "data": {"glossary": {...}, "terms": [...], ...}}
```

## Error Handling

All three exception types are importable from `katalogue`:

```python
from katalogue import KatalogueClient, ConfigError, AuthError, ApiError

try:
    client = KatalogueClient()
    systems = client.get("system", fields=["system_id", "system_name"])
except ConfigError as e:
    # Missing or invalid credentials — check env vars / Settings arguments
    print(f"Config error: {e}")
except AuthError as e:
    # HTTP 401 — wrong credentials or revoked token
    print(f"Auth failed: {e}")
except ApiError as e:
    # HTTP 4xx/5xx — resource not found, server error, etc.
    print(f"API error: {e}")
```

## OAuth2

The client handles the full OAuth2 client credentials flow internally:

- Fetches a token automatically on the first request
- Caches the token and re-uses it across calls
- Refreshes the token when it expires (on 401 response)
- Derives the OAuth2 scope from the resource name (`system.read`, `datasource.read`, etc.)

You never need to manage tokens manually.

## API Reference

| Symbol | Type | Description |
|--------|------|-------------|
| `KatalogueClient` | class | HTTP client; OAuth2 managed internally |
| `KatalogueClient.get()` | method | High-level fetch with filtering, sorting, and formatting |
| `Settings` | Pydantic model | Frozen configuration object |
| `resolve_settings()` | function | Build `Settings` from explicit args, env vars, or defaults |
| `filter_fields()` | function | Keep only named fields from a dict or list of dicts |
| `filter_resultset()` | function | Keep only rows matching a key/value condition |
| `sort_resultset()` | function | Sort a list of dicts by one or more columns, nulls last |
| `format_descriptions_to_plaintext()` | function | Convert rich-text description fields to plain text |
| `format_resultset()` | function | Route data to json/compact/Python-object format |
| `format_json()` | function | Pretty-print data as a JSON string |
| `format_compact_json()` | function | Compact JSON string with no spaces |
| `ConfigError` | exception | Missing credentials or invalid URL at construction time |
| `AuthError` | exception | HTTP 401 — authentication failed |
| `ApiError` | exception | Any other HTTP error (4xx, 5xx) |
| `TokenCache` | protocol | Interface for custom token cache backends |
| `TokenEntry` | Pydantic model | Single cached token; implement `TokenCache` with this |
| `DEFAULT_BASE_URL` | `str` | `"https://your-instance.katalogue.se"` |
| `DEFAULT_TOKEN_URL` | `str` | `"https://your-instance.katalogue.se/oidc/token"` |
