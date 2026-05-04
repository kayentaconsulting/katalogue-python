# Katalogue — Monorepo

Two packages in a `uv` workspace:

- **`katalogue-sdk`** — all business logic: HTTP, OAuth2, filtering, sorting, formatting, templating, file output
- **`katalogue-cli`** — thin Click wrapper: parse args → `client.get()` → emit result. Nothing else.

**If logic can live in the SDK, it must. The CLI adds no features of its own.**

## Setup

```bash
export KATALOGUE_CLIENT_ID=your-client-id
export KATALOGUE_CLIENT_SECRET=your-client-secret
export KATALOGUE_URL=https://your-instance.katalogue.se   # optional
```

## Commands

```bash
uv sync                                           # install workspace deps
uv run pytest -q                                  # all tests
uv run pytest packages/katalogue-sdk/tests        # SDK only
uv run pytest packages/katalogue-cli/tests        # CLI only
uv run ruff check --fix && uv run ruff format     # lint + format
uv run pyright                                    # type-check
uv run python smoke_tests.py                      # live smoke tests (needs env vars)
```

Run lint → type-check → tests after every change. Fix all failures before declaring done.

## Architecture

| Layer | Location | Responsibility |
|-------|----------|---------------|
| SDK client | `client/api.py` | HTTP, OAuth2, typed errors (`AuthError`, `ApiError`) |
| SDK models | `options.py`, `results.py` | `GetOptions`, `OutputOptions`, `CatalogResult` (Pydantic) |
| SDK output | `output.py`, `rendering.py`, `formatters.py` | Serialize, template, write/split files |
| SDK data | `exporting.py`, `filters.py` | Assemble hierarchical results, apply filters |
| CLI commands | `cli/<resource>.py` | Parse args → `run_get()` → done |
| CLI formatters | `formatters/` | Table rendering for TTY only |

The SDK has no Click dependency. Any Click import belongs in `katalogue-cli`.

## Key Files

```
packages/katalogue-sdk/src/katalogue/
  client/api.py      # KatalogueClient — single entry point: get()
  options.py         # GetOptions, OutputOptions
  output.py          # OutputPipeline — render, write, split
  formatters.py      # format_json/yaml/csv/compact/table, format_resultset()
  rendering.py       # Jinja2 sandbox, auto_filename(), get_template_extension()
  templates/         # dbt_source.j2, column_mapping.j2, json_template.j2
  __init__.py        # public API surface

packages/katalogue-cli/src/katalogue_cli/cli/
  common.py          # run_get(), emit_result(), resolve_template_format(), shared decorators
  <resource>.py      # one file per resource — thin, no logic
```

## TDD

Tests first (RED) → implement (GREEN). Never write implementation before a failing test exists.

**Test boundaries, not internals:**
- **CLI tests** — assert stdout, exit code, and stderr. Never assert how `GetOptions` was constructed or what internal state was set.
- **SDK formatter/transformation tests** — assert what comes out (`result.data`, `result.output`, CSV rows, flattened structure). These are real boundary tests of pure functions.
- **Do not** test call counts, argument capture, or internal wiring — those break on refactors without catching real bugs.

Mock at `katalogue_cli.cli.common.KatalogueClient`, not at import sites in command files:

```python
def test_something(runner, cli_auth, mock_client, catalog_result):
    mock_client.get.return_value = catalog_result({"id": 1, "name": "Test"}, "json")
    result = runner.invoke(cli, [*cli_auth, "system", "get", "1"])
    assert result.exit_code == 0
```

Cover per slice: happy path (json + table), auth failure, API error, empty results.

## CLI Design Rules

- Resource-first: `katalogue system get <id>`
- Every resource has `list` and `get`
- `--format json|yaml|yml|json-compact|compact|csv|table`
- `--template dbt-source|column-mapping|json-template|./path.j2` — separate from `--format`
- When `--template` is given without explicit `--format`, the template's natural format is used. `resolve_template_format()` in `common.py` detects this via `ctx.get_parameter_source("fmt")`.
- Exit codes: 0 success, 1 API/user error, 2 CLI usage error — errors to stderr

## Code Style

- Pydantic `BaseModel` for all models — no plain dataclasses
- `SecretStr` for secrets, `field_validator` for validation
