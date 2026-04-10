# katalogue-sdk

Python client for [Katalogue](https://katalogue.se), based on the Katalogue REST API. 

## Installation

```bash
pip install katalogue-sdk
# or with uv
uv add katalogue-sdk
```

## Quick Start

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from katalogue_sdk import KatalogueClient, resolve_settings

vault = SecretClient(
    vault_url="https://your-vault.vault.azure.net",
    credential=DefaultAzureCredential(),
)
settings = resolve_settings(
    client_id=vault.get_secret("katalogue-client-id").value,
    client_secret=vault.get_secret("katalogue-client-secret").value,
)
client = KatalogueClient(settings)
systems = client.list_resource("system")
```

## Credentials

### Get Katalogue Credentials
[Create an OAuth2 client](https://docs.katalogue.se/using-katalogue/katalogue_cli_and_sdk/#granting-access-to-katalogue) in Katalogue to get the client credentials referred to in the following section.

### Production — Azure Key Vault (recommended)

Fetch credentials from Key Vault at startup using `DefaultAzureCredential` (works with Managed Identity, workload identity, or local `az login`). Never store the secret in the environment or in code.

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from katalogue_sdk import KatalogueClient, resolve_settings

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
from katalogue_sdk import KatalogueClient

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
from katalogue_sdk import KatalogueClient

load_dotenv()
client = KatalogueClient()
```

`Settings` is a frozen Pydantic model. `client_secret` is stored as `SecretStr` and never appears in `repr()` or logs.

## Resource Hierarchy

Resources form a hierarchy. Pass these strings as the `resource` / `parent_resource` arguments:

```
system
  └── datasource
        └── dataset-group
              └── dataset
                    └── field
glossary   (independent)
```

## Client Methods

### List all items of a resource type

```python
systems = client.list_resource("system")
# -> [{"system_id": "sys-001", "system_name": "CDP", ...}, ...]

datasources = client.list_resource("datasource")
glossaries  = client.list_resource("glossary")
```

### Get a single item by ID

```python
system = client.get_resource("system", "sys-001")
# -> {"system_id": "sys-001", "system_name": "CDP", ...}

ds = client.get_resource("datasource", "ds-001")
```

### List children filtered by parent

```python
# All datasources belonging to a system
datasources = client.list_by_parent("datasource", "system", "sys-001")

# All datasets in a datasource
datasets = client.list_by_parent("dataset", "datasource", "ds-001")

# All fields in a dataset
fields = client.list_by_parent("field", "dataset", "dsg-001")
```

### Export full system (all nested data in one call)

```python
export = client.get_system_export("sys-001")
# -> {"meta": {...}, "data": {"system": {...}, "datasources": [...], ...}}
```

### Export full glossary

```python
export = client.get_glossary_export("gl-001")
# -> {"meta": {...}, "data": {"glossary": {...}, "terms": [...], ...}}
```

## Error Handling

All three exception types are importable from `katalogue_sdk`:

```python
from katalogue_sdk import KatalogueClient, ConfigError, AuthError, ApiError

try:
    client = KatalogueClient()
    systems = client.list_resource("system")
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
| `Settings` | Pydantic model | Frozen configuration object |
| `resolve_settings()` | function | Build `Settings` from explicit args, env vars, or defaults |
| `ConfigError` | exception | Missing credentials or invalid URL at construction time |
| `AuthError` | exception | HTTP 401 — authentication failed |
| `ApiError` | exception | Any other HTTP error (4xx, 5xx) |
| `DEFAULT_BASE_URL` | `str` | `"https://demo-api.katalogue.se"` |
| `DEFAULT_TOKEN_URL` | `str` | `"https://demo-api.katalogue.se/oidc/token"` |
