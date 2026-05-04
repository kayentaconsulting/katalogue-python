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
      filters.py          # Filter model, FilterParser, apply_filter
      options.py          # GetOptions, OutputOptions (Pydantic)
      results.py          # CatalogResult, WrittenFile (Pydantic)
      formatters.py       # format_json, format_compact_json, format_resultset, format_table
      utils.py            # filter_fields, filter_resultset, sort_resultset, unwrap_list
      exporting.py        # assemble_system/datasource/dataset_group/dataset/glossary
      output.py           # OutputPipeline — render, write, split
      rendering.py        # Jinja2 sandbox, load_template, render_template, auto_filename
      templates/          # built-in Jinja2 templates (dbt_source.j2, column_mapping.j2)
      __init__.py         # public API surface: KatalogueClient, GetOptions, OutputOptions,
                          #   Filter, CatalogResult, WrittenFile, Settings, errors, TokenCache
    tests/
      conftest.py
      fixtures/           # JSON response fixtures
  katalogue-cli/
    src/katalogue_cli/
      auth.py             # disk-backed token cache (CLI layer)
      logging.py          # logging setup
      cli/
        main.py           # root Click group + global options
        common.py         # emit_result(), run_get(), build_get_options(), shared decorators
        auth.py           # login / logout / status commands
        <resource>.py     # one file per resource (system, datasource, dataset,
                          #   dataset_group, field, glossary)
      config/
        file.py           # reads ~/.config/katalogue/config.toml (non-secrets only)
      formatters/
        output.py         # format_output, format_list_table, format_grouped_table
        defaults.py       # DEFAULT_FIELDS, PARENT_GROUP per resource
    tests/
      conftest.py         # runner, cli_auth, mock_client, catalog_result fixtures
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
def test_something(runner, cli_auth, mock_client, catalog_result):
    mock_client.get.return_value = catalog_result({"id": 1, "name": "Test"}, "json")
    result = runner.invoke(cli, [*cli_auth, "system", "get", "1"])
    assert result.exit_code == 0
```

The `catalog_result` fixture builds a `CatalogResult` with `output` pre-populated for json/compact formats. For table format, set only `data` (the CLI renders it client-side):

```python
mock_client.get.return_value = CatalogResult(data=[{"system_id": 1, "system_name": "X"}])
```

Cover per slice: happy path (json + table), auth failure, API error, empty results, missing config.

Mock is patched at `katalogue_cli.cli.common.KatalogueClient` — not at the import site in each command file.

SDK tests go in `packages/katalogue-sdk/tests/`, CLI tests in `packages/katalogue-cli/tests/`.
`katalogue-sdk` has no Click dependency — keep it that way. Any Click import belongs in `katalogue-cli`.

## Architecture Layers

| Package | Layer | Does | Does Not |
|---------|-------|------|----------|
| `katalogue-sdk` | `client/` | HTTP requests, OAuth2, routing via `get()`, typed errors | Format output, know about Click |
| `katalogue-sdk` | `config/` | Resolve settings from env/defaults | Make HTTP calls |
| `katalogue-sdk` | `output.py` + `rendering.py` + `templates/` | Render json/compact/template output, write files, split by resource level | Table formatting, Click |
| `katalogue-cli` | `cli/` | Parse args, call `client.get()`, emit results, handle errors | Construct URLs, manage HTTP |
| `katalogue-cli` | `formatters/` | Table rendering for TTY | Know about HTTP, Click, or config |

## Code Preferences

- **Pydantic for all data models** — use `BaseModel` instead of `@dataclass`. Use `SecretStr` for secrets, `field_validator` for validation. Never introduce a plain dataclass when Pydantic can do the job.
