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
uv pip install "git+https://github.com/kayentaconsulting/katalogue-python.git#subdirectory=packages/katalogue-sdk"

# or with pip
pip install "git+https://github.com/kayentaconsulting/katalogue-python.git#subdirectory=packages/katalogue-sdk"
```

## Quick Start

```python
from katalogue import KatalogueClient, GetOptions

client = KatalogueClient()  # reads KATALOGUE_CLIENT_ID / KATALOGUE_CLIENT_SECRET from env

# List all systems
result = client.get("system")
print(result.data)  # list of dicts

# List systems — selected properties, sorted
result = client.get("system", GetOptions(
    properties=["system_id", "system_name"],
    sort=[{"system_name": "asc"}],
))

# Single record by ID
result = client.get("system", GetOptions(resource_id=1))

# All datasources under a system
result = client.get("datasource", GetOptions(parent_id=1))

# All PII fields — filtered client-side
result = client.get("field", GetOptions(
    filters=["is_pii=true"],
    properties=["field_id", "field_name", "dataset_name"],
))
```

## Public Surface

```python
from katalogue import (
    KatalogueClient,
    GetOptions,
    OutputOptions,
    Filter,
    CatalogResult,
    WrittenFile,
    Settings,
    resolve_settings,
    AuthError,
    ApiError,
    ConfigError,
    TokenCache,
    TokenEntry,
    DatatypeConverterConfig,
    load_datatype_converter,
)
```

Internal helpers (`filter_properties`, `sort_resultset`, `format_json`, etc.) are available from their submodules (`katalogue.utils`, `katalogue.formatters`) for advanced use cases.

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

`get()` is the single entry point for querying resources. Pass a `GetOptions` object to control routing, filtering, sorting, and output. All filtering and sorting happens **client-side** after the API fetch.

```python
from katalogue import KatalogueClient, GetOptions, OutputOptions

result = client.get(resource, options=GetOptions(...))
# result.data          — filtered/sorted Python object (dict or list of dicts)
# result.raw           — unprocessed API response
# result.output        — formatted string (set when OutputOptions.format or .template is set)
# result.output_file   — path written to (set when OutputOptions.output_file is used)
# result.output_files  — list of WrittenFile (set when OutputOptions.split_by is used)
# result.metadata["strategy"] — "single" | "list" | "list_by_parent"
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
result = client.get("system", GetOptions(properties=["system_id", "system_name", "system_type"]))
# result.data -> [{"system_id": 1, "system_name": "Katalogue", "system_type": "Data Catalog"}, ...]
```

### Single record

```python
result = client.get("system", GetOptions(resource_id=1))
# result.data -> {"system_id": 1, "system_name": "Katalogue", ...}
```

### Children by parent

Walk the full hierarchy: system → datasource → dataset_group → dataset → field.

```python
datasources = client.get("datasource", GetOptions(parent_id=1, properties=["datasource_id", "datasource_name"])).data

dataset_groups = client.get("dataset_group", GetOptions(
    parent_id=datasources[0]["datasource_id"],
    properties=["dataset_group_id", "dataset_group_name"],
)).data

datasets = client.get("dataset", GetOptions(
    parent_id=dataset_groups[0]["dataset_group_id"],
    properties=["dataset_id", "dataset_name"],
)).data

fields = client.get("field", GetOptions(
    parent_id=datasets[0]["dataset_id"],
    properties=["field_id", "field_name", "data_type", "is_pii"],
)).data
```

### Scoped lookup

Returns `data=None` if the record doesn't belong to the given parent.

```python
result = client.get("field", GetOptions(resource_id=42, parent_id=10))
# result.data -> record if field 42 is in dataset 10, else None
```

### Filter

AND-logic filter strings, applied client-side. Syntax: `path OP value`.

```python
result = client.get("field", GetOptions(
    filters=["is_pii=true"],
    properties=["field_id", "field_name", "dataset_name", "datasource_name", "is_pii"],
))

# Multiple filters are ANDed together
result = client.get("field", GetOptions(
    filters=["is_pii=true", 'datatype_fullname="varchar"'],
))

# Dotted-path filter scoped to a nested level
result = client.get("system", GetOptions(
    include_children=True,
    resource_id=1,
    filters=['field.is_pii=true'],  # only keep fields where is_pii is true
))
```

Operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `contains`, `startswith`, `endswith`.
String operators (`=`, `contains`, `startswith`, `endswith`) are case-insensitive.
Boolean values are matched tolerantly: `true` and `false` match both the JSON boolean form and any casing of the string form (`"true"`, `"True"`, `"TRUE"`).

### Sort

Multi-column. `"asc"` and `"desc"` are case-insensitive. Null values always sort last.

```python
result = client.get("system", GetOptions(
    sort=[{"system_name": "asc"}],
    properties=["system_id", "system_name"],
))

# Multi-column: primary key first
result = client.get("field", GetOptions(sort=[{"dataset_name": "asc"}, {"field_name": "asc"}]))
```

### Plain-text descriptions

Description fields are stored as rich-text JSON. Pass `format_descriptions_as_text=True` to extract plain text.

```python
result = client.get("system", GetOptions(
    properties=["system_id", "system_name", "system_description"],
    format_descriptions_as_text=True,
))
# result.data -> [{"system_id": 1, "system_name": "Katalogue", "system_description": "User-friendly system..."}]
```

### Serialization formats

Pass `OutputOptions(format=...)` to serialize the result as a string in `result.output`.

```python
from katalogue import KatalogueClient, GetOptions, OutputOptions

# JSON (pretty-printed)
result = client.get("system", GetOptions(output=OutputOptions(format="json")))
print(result.output)   # '[\n  {\n    "system_id": 1, ...'

# YAML (also accepts "yml")
result = client.get("system", GetOptions(output=OutputOptions(format="yaml")))

# Compact JSON — single line, no whitespace (also accepts "compact")
result = client.get("system", GetOptions(output=OutputOptions(format="json-compact")))

# CSV — flat list serialized directly; hierarchical data flattened to lowest level
result = client.get("field", GetOptions(output=OutputOptions(format="csv")))

# CSV with include_children — flattened to field level, parent columns denormalized per row
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(format="csv"),
))
```

### Validation

`resource` and sort `direction` are validated. Invalid values raise `ValueError`.

```python
client.get("ssystem")
# ValueError: Invalid resource 'ssystem'. Must be one of: dataset, dataset_group, datasource, field, glossary, system

client.get("system", GetOptions(sort=[{"system_name": "ascending"}]))
# ValueError: Invalid sort direction 'ascending' for column 'system_name'. Must be 'asc' or 'desc'.
```

## Hierarchical Retrieval

Pass `include_children=True` with `resource_id` to fetch a resource and all its descendants in a single call. The result uses a flat canonical shape with all child records in separate top-level lists.

```python
from katalogue import KatalogueClient, GetOptions

result = client.get("system", GetOptions(resource_id=1, include_children=True))
# result.data -> {
#   "resource": "system",
#   "system": {"system_id": 1, "system_name": "..."},
#   "datasources": [...],
#   "dataset_groups": [...],
#   "datasets": [...],
#   "fields": [...],
# }
```

Supported for `system`, `datasource`, `dataset_group`, `dataset`, and `glossary`.

Hierarchical filters scope to the named level — only records at that level are pruned; ancestors are retained:

```python
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    filters=["field.is_pii=true"],   # keep only PII fields
))
```

## Templated Export

Combine `include_children=True` with `OutputOptions(template=...)` to render the result using a built-in or custom Jinja2 template. Templates and serialization formats are independent axes.

### Built-in templates

| Name | Natural format | Description |
|------|----------------|-------------|
| `dbt-source` | YAML | dbt `sources.yml` structure |
| `column-mapping` | YAML | Field-level column mapping |
| `json-template` | JSON | Full hierarchical context as a JSON object |
| `nested-yml` | YAML | Nested object/array fields rendered as indented YAML |

### Template only — natural format

```python
from katalogue import KatalogueClient, GetOptions, OutputOptions

# dbt-source renders YAML
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(template="dbt-source"),
))
print(result.output)   # YAML string starting with "version: 2\nsources:\n..."

# json-template renders JSON
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(template="json-template"),
))
print(result.output)   # JSON string
```

### Template + format — convert output

Combine `template` and `format` to convert the rendered output to a different serialization format:

```python
# dbt-source (YAML) converted to JSON
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(template="dbt-source", format="json"),
))
print(result.output)   # JSON string

# dbt-source (YAML) converted to compact JSON
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(template="dbt-source", format="json-compact"),
))

# json-template (JSON) converted to YAML
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(template="json-template", format="yaml"),
))
```

### Custom template

You can either pass a direct `.j2` path or register templates in a repo-local
config file.

`katalogue.toml` in the repository root:

```toml
[templates.dbt-source]
path = "templates/dbt-source.j2"
default_format = "yaml"

[templates.customer-mapping]
path = "templates/customer-mapping.j2"
default_format = "json"
```

`pyproject.toml`:

```toml
[tool.katalogue.templates.dbt-source]
path = "templates/dbt-source.j2"
default_format = "yaml"

[tool.katalogue.templates.customer-mapping]
path = "templates/customer-mapping.j2"
default_format = "json"
```

Registry entries use the logical name passed to `template=...`, plus the source
path and default output format. If a repo defines the same name as a built-in
template, the repo version wins.

Templates receive a small set of domain helpers in the Jinja2 context:

- `field_type(f)`, `field_desc(f)`, `field_is_pii(f)`, `field_is_primary_key(f)` — collapse the multi-key fallback chains for each field property
- `dataset_desc(ds)` — same for dataset descriptions
- `fields_tree(dataset_id=None)` — reshape the flat `fields` list into a `parent_field_id` tree (each node has a `children` list and a dotted `field_path`), so nested-column templates use Jinja2's `{% for ... recursive %}` loop instead of hand-written macros

See [docs/custom-templates.md](../../docs/custom-templates.md) for the full reference and copy-paste recipes.

To share reusable Jinja2 macro files across templates, register macro search paths in the same config file:

`katalogue.toml`:

```toml
[macro_paths]
paths = ["macros/"]
```

`pyproject.toml`:

```toml
[tool.katalogue.macro_paths]
paths = ["macros/"]
```

Macro files placed next to a `.j2` template file are also importable automatically, with no config needed. See [docs/custom-templates.md](../../docs/custom-templates.md) for the full reference.

Pass a path to a `.j2` file directly:

```python
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(template="./my_template.j2"),
))
```

### Single file output

```python
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(template="dbt-source", output_file="./sources.yml"),
))
# result.output_file -> "./sources.yml"
```

### Split by resource level

Write one file per dataset (or datasource, or dataset_group):

```python
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(
        template="dbt-source",
        split_by="dataset",
        output_dir="./dbt/models",
    ),
))
for f in result.output_files:
    print(f.path)   # ./dbt/models/customers.yml, ./dbt/models/orders.yml, ...
```

File extensions are derived from the format or template:

| Setting | Extension |
|---------|-----------|
| `format="json"` | `.json` |
| `format="yaml"` or `"yml"` | `.yaml` |
| `format="csv"` | `.csv` |
| built-in or repo-registered template with default format `yaml` / `yml` | `.yaml` / `.yml` |
| built-in or repo-registered template with default format `json` | `.json` |
| custom `.j2` file (no format) | `.yml` |

`format` takes precedence over `template` when determining the extension.

### Dry run

```python
result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    output=OutputOptions(
        template="dbt-source",
        split_by="dataset",
        output_dir="./out",
        dry_run=True,
    ),
))
# Files are planned but not written. result.output_files lists what would be created.
```

## Low-Level Client Methods

These are available for advanced use cases where you need direct control over API calls. They return the raw API envelope without any filtering or formatting applied.

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
    result = client.get("system", GetOptions(properties=["system_id", "system_name"]))
    systems = result.data
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
| `KatalogueClient.get()` | method | High-level fetch with filtering, sorting, and output |
| `GetOptions` | Pydantic model | Routing, filter, sort, properties, output options |
| `GetOptions.resource_id` | `int \| str \| None` | Fetch a single resource by ID |
| `GetOptions.parent_id` | `int \| str \| None` | Fetch all children of a parent |
| `GetOptions.filters` | `list[str] \| None` | Client-side filter expressions |
| `GetOptions.properties` | `list[str] \| None` | Columns to keep in the result |
| `GetOptions.sort` | `list[dict] \| None` | Multi-column sort, e.g. `[{"name": "asc"}]` |
| `GetOptions.include_children` | `bool` | Fetch resource and all descendants |
| `GetOptions.format_descriptions_as_text` | `bool` | Convert Draft.js rich-text to plain text |
| `GetOptions.datatype_converter` | `str \| None` | Built-in name, registered name, or `.yaml` / `.yml` path - adds `datatype_converted` to each field record |
| `GetOptions.output` | `OutputOptions` | Output rendering and file options |
| `OutputOptions` | Pydantic model | Serialization, template, file output, split-by, dry-run |
| `OutputOptions.format` | `str \| None` | Serialization format: `json`, `yaml`, `yml`, `json-compact`, `compact`, `csv` |
| `OutputOptions.template` | `str \| None` | Built-in template name or path to a `.j2` file |
| `OutputOptions.output_file` | `str \| None` | Write output to this file path |
| `OutputOptions.output_dir` | `str \| None` | Directory for split output files |
| `OutputOptions.split_by` | `str \| None` | Split level: `datasource`, `dataset_group`, `dataset` |
| `OutputOptions.filename_template` | `str \| None` | Jinja2 expression for naming split files |
| `OutputOptions.overwrite` | `bool` | Overwrite existing files (default `False`) |
| `OutputOptions.dry_run` | `bool` | Plan files without writing them (default `False`) |
| `Filter` | Pydantic model | Parsed filter expression (path, operator, value) |
| `CatalogResult` | Pydantic model | Result envelope: data, raw, output, output_file, output_files |
| `WrittenFile` | Pydantic model | Single written file record from a split export |
| `Settings` | Pydantic model | Frozen configuration object |
| `resolve_settings()` | function | Build `Settings` from explicit args, env vars, or defaults |
| `ConfigError` | exception | Missing credentials or invalid URL at construction time |
| `AuthError` | exception | HTTP 401 — authentication failed |
| `ApiError` | exception | Any other HTTP error (4xx, 5xx) |
| `TokenCache` | protocol | Interface for custom token cache backends |
| `TokenEntry` | Pydantic model | Single cached token; implement `TokenCache` with this |
| `DatatypeConverterConfig` | Pydantic model | Loaded datatype converter: `source`, `target`, `mappings: dict[str, str]` |
| `load_datatype_converter()` | function | Resolve and load a datatype converter by built-in name, registered name, or `.yaml` / `.yml` path |

## Custom Datatype Converters

Create your own datatype converter by writing a YAML file with `source`, `target`, and a `mappings` table:

```yaml
source: oracle
target: snowflake
mappings:
  VARCHAR2: VARCHAR
  NUMBER: "NUMBER{args}"
  TIMESTAMP WITH TIME ZONE: TIMESTAMP_LTZ
```

`{args}` preserves the original parenthesised suffix, so `NUMBER(10,2)` stays `NUMBER(10,2)` while `NUMBER` stays `NUMBER`.

You can use it in either of these ways:

- pass the file path directly to `GetOptions.datatype_converter`
- register the file in `katalogue.toml` or `[tool.katalogue.datatype_converters]` in `pyproject.toml`

Repo-registered names override built-ins with the same name. Both `.yaml` and `.yml` file paths are supported. See [docs/datatype-converter.md](../../docs/datatype-converter.md) for the full reference.
