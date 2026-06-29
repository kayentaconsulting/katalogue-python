# SDK client and authentication

`katalogue-sdk` is a standalone Python client for the Katalogue REST API. It has no
Click or CLI dependency and can be used in scripts, notebooks, services, and agents.

For installation and a first script, see [Getting started](../getting-started.md).
For the full options/result model reference, see [Options and results](options.md).

## Contents

- [Public surface](#public-surface)
- [Creating a client](#creating-a-client)
- [Credentials](#credentials)
- [Resource hierarchy](#resource-hierarchy)
- [Error handling](#error-handling)
- [OAuth2 and token caching](#oauth2-and-token-caching)
- [Low-level client methods](#low-level-client-methods)

## Public surface

Everything you need is importable directly from `katalogue`:

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

Internal helpers (`filter_properties`, `sort_resultset`, `format_json`, etc.) live in
submodules (`katalogue.utils`, `katalogue.formatters`) for advanced use cases.

## Creating a client

```python
from katalogue import KatalogueClient

client = KatalogueClient()  # reads KATALOGUE_CLIENT_ID / _SECRET / _URL from the environment
```

`client.get()` is the single high-level entry point — see
[Options and results](options.md) for everything it can do:

```python
from katalogue import KatalogueClient, GetOptions

client = KatalogueClient()
result = client.get("system")
print(result.data)  # list of dicts
```

To pass credentials explicitly instead of via the environment, build a `Settings`
object with `resolve_settings()`:

```python
from katalogue import KatalogueClient, resolve_settings

settings = resolve_settings(
    client_id="...",
    client_secret="...",
    base_url="https://your-instance.katalogue.se",
)
client = KatalogueClient(settings)
```

`resolve_settings()` precedence is **explicit argument > environment variable >
default**. `token_url` defaults to `<base_url>/oidc/token`. `Settings` is a frozen
Pydantic model; `client_secret` is stored as `SecretStr` and never appears in
`repr()` or logs.

## Credentials

Get credentials by [creating an OAuth2 client](https://docs.katalogue.se/using-katalogue/katalogue_cli_and_sdk/#granting-access-to-katalogue)
in Katalogue.

### Production — Azure Key Vault (recommended)

Fetch credentials from Key Vault at startup using `DefaultAzureCredential` (works
with Managed Identity, workload identity, or local `az login`). Never store the
secret in the environment or in code.

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
    base_url="https://your-instance.katalogue.se",
)
client = KatalogueClient(settings)
```

```bash
uv add katalogue-sdk azure-identity azure-keyvault-secrets
```

In Azure-hosted services (Functions, Container Apps, AKS) this means zero
credentials in the app — assign the Managed Identity read access to the vault.

### CI/CD pipelines

Inject secrets as environment variables from your pipeline's secret store. The SDK
picks them up automatically:

```bash
KATALOGUE_CLIENT_ID=...
KATALOGUE_CLIENT_SECRET=...
KATALOGUE_URL=https://your-instance.katalogue.se                    # optional
KATALOGUE_TOKEN_URL=https://your-instance.katalogue.se/oidc/token   # optional
```

```python
from katalogue import KatalogueClient

client = KatalogueClient()  # reads env vars
```

### Local development

Use a `.env` file (never commit it) and load it before constructing the client:

```python
from dotenv import load_dotenv
from katalogue import KatalogueClient

load_dotenv()
client = KatalogueClient()
```

## Resource hierarchy

Pass these strings as the `resource` argument to `get()`:

```
system
  └── datasource
        └── dataset_group
              └── dataset
                    └── field
glossary   (independent)
```

Note the SDK uses underscores (`dataset_group`), while the CLI uses hyphens
(`dataset-group`).

## Error handling

All three exception types are importable from `katalogue`:

```python
from katalogue import KatalogueClient, GetOptions, ConfigError, AuthError, ApiError

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

`get()` also raises `ValueError` for an invalid `resource` name or sort direction.

## OAuth2 and token caching

The client handles the full OAuth2 client-credentials flow internally:

- Fetches a token automatically on the first request
- Caches the token and re-uses it across calls
- Refreshes the token when it expires (on a 401 response)
- Derives the OAuth2 scope from the resource name (`system.read`, `datasource.read`, …)

You never need to manage tokens manually. By default the cache is in-memory. To
persist tokens (or back them with Redis, a file, etc.), implement the `TokenCache`
protocol and pass it in:

```python
from katalogue import KatalogueClient, TokenCache, TokenEntry

class MyCache:  # conforms to the TokenCache protocol
    def get(self, key: str) -> TokenEntry | None: ...
    def set(self, key: str, entry: TokenEntry) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...

client = KatalogueClient(token_cache=MyCache())
```

## Low-level client methods

For advanced use cases that need direct control over API calls. These return the
raw API envelope without filtering or formatting.

```python
client.list_resource("system")
# -> {"systems": [{"system_id": 1, ...}, ...]}

client.get_resource("system", 1)
# -> {"system_id": 1, "system_name": "Katalogue", ...}

client.list_by_parent("datasource", "system", 1)
# -> [{"datasource_id": 1, ...}, ...]

client.get_system_export(1)
# -> {"meta": {...}, "data": {"system": {...}, "datasources": [...], ...}}

client.get_glossary_export(1)
# -> {"meta": {...}, "data": {"glossary": {...}, "terms": [...], ...}}
```

Prefer `get()` for everyday use — it adds routing, filtering, sorting, and output
rendering on top of these.
