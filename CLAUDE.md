# Katalogue — Monorepo

Python uv workspace containing two packages:
- **`katalogue-sdk`** — standalone HTTP client + OAuth2, usable without Click
- **`katalogue-cli`** — Click CLI that wraps the SDK

## Prerequisites

You need OAuth2 client credentials for a Katalogue instance. Set these before running any command:

```bash
export KATALOGUE_CLIENT_ID=your-client-id
export KATALOGUE_CLIENT_SECRET=your-client-secret
export KATALOGUE_URL=https://your-instance.katalogue.se        # optional, defaults to demo
export KATALOGUE_TOKEN_URL=https://your-instance.katalogue.se/oidc/token  # optional
```

For per-project dev credentials, use [`direnv`](https://direnv.net/) with an `.envrc` file — the CLI reads standard environment variables and does not load `.env` files.

With env vars set, both of these work:
```python
from katalogue import KatalogueClient
client = KatalogueClient()          # reads env vars
client = KatalogueClient(settings)  # explicit settings object
```

## Commands

```bash
uv sync                    # install all workspace deps
uv run pytest              # run all tests (both packages)
uv run pytest -v           # verbose
uv run pytest -k system    # filter by name
uv run pytest packages/katalogue-sdk/tests   # SDK only
uv run pytest packages/katalogue-cli/tests   # CLI only
uv run katalogue --help    # try the CLI

# run after every logical unit of work — all three, in order
uv run ruff check --fix && uv run ruff format   # lint + format
uv run pyright                                   # type-check
uv run pytest -q                                 # verify nothing broke
```

If any check fails, fix before declaring the task complete.

## Directory Structure

```
packages/
  katalogue-sdk/
    src/katalogue/
      client/api.py       # KatalogueClient — HTTP + OAuth2, raises AuthError/ApiError
      client/cache.py     # TokenCache protocol + in-memory impl
      config/settings.py  # resolve_settings() — explicit > env var > default (Pydantic)
      __init__.py         # public API surface: KatalogueClient, Settings, errors
    tests/
      conftest.py
      fixtures/           # JSON response fixtures
  katalogue-cli/
    src/katalogue_cli/
      auth.py             # disk-backed token cache (CLI layer)
      logging.py          # logging setup
      cli/
        main.py           # root Click group + global options
        common.py         # handle_api_call(), filter_fields(), shared decorators
        auth.py           # login / logout / status commands
        <resource>.py     # one file per resource (system, datasource, dataset,
                          #   dataset_group, field, glossary, export)
      config/
        file.py           # reads ~/.config/katalogue/config.toml (non-secrets only)
      formatters/
        output.py         # format_json, format_table, format_compact_json
    tests/
      conftest.py         # runner, cli_auth, mock_client fixtures
      fixtures/           # JSON response fixtures
pyproject.toml            # uv workspace root — no code, just workspace + pytest config
pyrightconfig.json        # IDE static analysis config
```

## TDD Workflow (Non-Negotiable)

Every feature slice: **tests first (RED) → implement (GREEN) → review done**.

**Never write implementation before tests exist and are failing.**

## CLI Design Rules

- **Resource-first**: `katalogue system get <id>` — not verb-first, not API-mirror
- **Consistent verbs**: every resource has `list` and `get`
- **Parent filtering**: `--<parent> <id>` flag on `list` commands
- **Output formats**: `--format json|table|compact`; JSON when piped, table on TTY
- **Exit codes**: 0 success, 1 API/user error, 2 CLI usage error
- **Errors to stderr** with what happened + what to do

## Testing Patterns

Mock at the client layer using the shared `mock_client` fixture:

```python
def test_something(runner, cli_auth, mock_client):
    mock_client.get_resource.return_value = {"id": 1, "name": "Test"}
    result = runner.invoke(cli, [*cli_auth, "system", "get", "1"])
    assert result.exit_code == 0
```

Cover per slice: happy path (json + table), auth failure, API error, empty results, missing config.

Mock is patched at `katalogue_cli.cli.common.KatalogueClient` — not at the import site in each command file.

SDK tests go in `packages/katalogue-sdk/tests/`, CLI tests in `packages/katalogue-cli/tests/`.
`katalogue-sdk` has no Click dependency — keep it that way. Any Click import belongs in `katalogue-cli`.

## Architecture Layers

| Package | Layer | Does | Does Not |
|---------|-------|------|----------|
| `katalogue-sdk` | `client/` | HTTP requests, parse responses, raise typed errors | Format output, know about Click |
| `katalogue-sdk` | `config/` | Resolve settings from env/defaults | Make HTTP calls |
| `katalogue-cli` | `cli/` | Parse args, call client, format output, handle errors | Construct URLs, manage HTTP |
| `katalogue-cli` | `formatters/` | Turn dicts into strings | Know about HTTP, Click, or config |

## Code Preferences

- **Pydantic for all data models** — use `BaseModel` instead of `@dataclass`. Use `SecretStr` for secrets, `field_validator` for validation. Never introduce a plain dataclass when Pydantic can do the job.
