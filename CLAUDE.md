# Katalogue CLI

Python Click CLI for the Katalogue Data Catalog API. Works for both human developers and AI agents.

## Quick Commands

```bash
uv sync                    # install deps
uv run pytest              # run all tests
uv run pytest -v           # verbose
uv run pytest -k system    # filter by name
uv run katalogue --help    # try the CLI
```

## Current Status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M1: Foundation + `system get` | **DONE** | 21 tests passing |
| M2: Generic CRUD client | **DONE** | `list_resource`, `get_resource`, `list_by_parent` all implemented |
| M3: System + Datasource commands | **DONE** | list/get/children all implemented and tested |
| M4: Dataset group + Dataset + Field | **DONE** | list/get/children all implemented and tested |
| M5: Export + Task/Job commands | **Partial** | export done; task/job not started |
| M6: Polish and Package | **DONE** | help text reviewed, README updated, `--version` done |

**Bonus (unplanned)**: `glossary list/get` implemented and tested.

Full milestone details in `PROJECT_PLAN.md`.

## TDD Workflow (Non-Negotiable)

Every feature slice:
1. **Atlas** maps endpoints → **Mira** designs UX → **Kai** proposes structure → **Vera** writes test plan
2. Write all tests first — they must fail (RED)
3. Implement until tests pass (GREEN)
4. **Reed** reviews layering → **Dana** reviews UX → declare done

**Never write implementation before tests exist and are failing.**

Agent definitions: `.claude/agents/<name>.md`

## Key Files

| File | Purpose |
|------|---------|
| `src/katalogue/cli/main.py` | Root Click group, global options, group registration |
| `src/katalogue/cli/common.py` | `get_client()`, `handle_api_call()`, `filter_fields()`, shared decorators |
| `src/katalogue/client/api.py` | `KatalogueClient` — HTTP + OAuth2 client credentials |
| `src/katalogue/config/settings.py` | `resolve_settings()` — CLI flag > env var > default |
| `src/katalogue/formatters/output.py` | `format_json`, `format_table`, `format_compact_json` |
| `tests/conftest.py` | Shared fixtures: `runner`, `cli_auth`, `mock_client` |

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

## Architecture Layers

| Layer | Does | Does Not |
|-------|------|----------|
| `cli/` | Parse args, call client, format output, handle errors | Construct URLs, manage HTTP |
| `client/` | HTTP requests, parse responses, raise typed errors | Format output, know about Click |
| `config/` | Resolve settings from flags/env/defaults | Make HTTP calls |
| `formatters/` | Turn dicts into strings | Know about HTTP, Click, or config |

## Working Style

- Be opinionated — push back on weak design
- Small reviewable steps — no big code dumps
- Wait for input before generating large amounts of code
- Agent team is a lens, not separate participants — present one recommendation
