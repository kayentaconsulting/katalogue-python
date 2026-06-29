# Getting started

Katalogue ships two packages that share one core:

| Package | Use it for |
|---------|------------|
| `katalogue-cli` | Interactive use and shell scripting from a terminal |
| `katalogue-sdk` | Scripts, notebooks, services, and agents in Python |

The CLI is a thin wrapper over the SDK, so both authenticate the same way and expose
the same capabilities. This guide gets you from zero to your first result with either.

## 1. Install

The CLI includes the SDK as a dependency. Install whichever you need:

```bash
# CLI (includes the SDK)
pip install katalogue-cli

# SDK only
pip install katalogue-sdk
```

(Or with `uv`: `uv add katalogue-cli` / `uv add katalogue-sdk`.)

## 2. Get API access

The SDK and CLI talk to the Katalogue REST API using OAuth2 client credentials. You
need the REST API enabled and an OIDC client with the right scopes. Follow
[Granting access to Katalogue](https://docs.katalogue.se/using-katalogue/katalogue_cli_and_sdk/#granting-access-to-katalogue)
to create a client and obtain a **client ID** and **client secret**.

You will configure three values:

| Setting | Env var | Notes |
|---------|---------|-------|
| Client ID | `KATALOGUE_CLIENT_ID` | required |
| Client secret | `KATALOGUE_CLIENT_SECRET` | required; keep it out of shell history |
| Base URL | `KATALOGUE_URL` | your instance, e.g. `https://your-instance.katalogue.se` |

The token URL defaults to `<base-url>/oidc/token` and rarely needs setting
(`KATALOGUE_TOKEN_URL` to override).

## 3. First command (CLI)

The quickest way to store credentials is `auth login`, which saves the client ID,
base URL, and token URL to a config file and the secret to your OS keychain:

```bash
katalogue auth login        # prompts for client ID, secret, and base URL
katalogue auth status       # confirm what's set
katalogue system list       # your first call
```

Prefer environment variables (e.g. in CI)? Set the three vars above and skip
`auth login`:

```bash
export KATALOGUE_CLIENT_ID=...
export KATALOGUE_CLIENT_SECRET=...
export KATALOGUE_URL=https://your-instance.katalogue.se
katalogue system list
```

From here:
- Browse [the command reference](cli/commands.md)
- Learn [filtering and property selection](reference/filtering.md)
- Choose [output formats and write files](cli/output-formats.md)

## 4. First script (SDK)

```python
from katalogue import KatalogueClient, GetOptions

client = KatalogueClient()  # reads KATALOGUE_CLIENT_ID / _SECRET / _URL from the environment

# List all systems
result = client.get("system")
print(result.data)  # list of dicts

# All PII fields, just the columns you want
result = client.get("field", GetOptions(
    filters=["is_pii=true"],
    properties=["field_id", "field_name", "dataset_name"],
))
print(result.data)
```

From here:
- [SDK client and authentication](sdk/client.md) — credentials, errors, token caching
- [Options and results](sdk/options.md) — everything `get()` can do
- [Filtering and selection](reference/filtering.md) — filter syntax

## 5. Go further

- [Exporting](guides/exporting.md) — pull a full hierarchy and write it to files
- [Templates](guides/templates.md) — render dbt sources, column mappings, or your own Jinja2
- [Datatype conversion](guides/datatype-conversion.md) — map source types to Databricks/PySpark/…
- [Troubleshooting](reference/troubleshooting.md) — auth and configuration issues

Stuck? See [Troubleshooting](reference/troubleshooting.md) or the full
[documentation index](index.md).
