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

## Directory Structure

```
src/katalogue/
  cli/          # Click commands — arg parsing, error handling, output formatting
  client/       # KatalogueClient — HTTP + OAuth2, raises AuthError/ApiError
  config/       # resolve_settings() — CLI flag > env var > default (Pydantic)
  formatters/   # format_json, format_table, format_compact_json
tests/
  conftest.py   # runner, cli_auth, mock_client fixtures
  fixtures/     # JSON response fixtures
```

## TDD Workflow (Non-Negotiable)

Every feature slice follows this order — **no exceptions**:

1. **Atlas** maps endpoints → **Mira** designs UX → **Kai** proposes structure → **Sven** flags security risks → **Vera** writes test plan
2. Write tests first (RED) → implement (GREEN)
3. **Reed** reviews layering → **Dana** reviews UX → **Sven** signs off security → declare done

**Before writing any code**, narrate each agent's verdict explicitly in the response. No implementation until Atlas → Vera have signed off. No slice is done until Reed, Dana, and Sven have reviewed.

**Never write implementation before tests exist and are failing.**

### Agent Narration Format

Each agent verdict must use this format so they're scannable:

```
🗺️ [ATLAS]  — <endpoint/data finding>
🎨 [MIRA]   — <UX decision>
🏗️ [KAI]    — <structure/approach>
🛡️ [SVEN]   — <security assessment>
✅ [VERA]   — <test plan>
--- implement ---
🔧 [REED]   — <layering verdict>
💬 [DANA]   — <DX/done verdict>
🛡️ [SVEN]   — <security sign-off>
```

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

Mock is patched at `katalogue.cli.common.KatalogueClient` — not at the import site in each command file.

## Architecture Layers

| Layer | Does | Does Not |
|-------|------|----------|
| `cli/` | Parse args, call client, format output, handle errors | Construct URLs, manage HTTP |
| `client/` | HTTP requests, parse responses, raise typed errors | Format output, know about Click |
| `config/` | Resolve settings from flags/env/defaults | Make HTTP calls |
| `formatters/` | Turn dicts into strings | Know about HTTP, Click, or config |

## Code Preferences

- **Pydantic for all data models** — use `BaseModel` instead of `@dataclass`. Use `SecretStr` for secrets, `field_validator` for validation. Never introduce a plain dataclass when Pydantic can do the job.

## Working Style

- Be opinionated — push back on weak design
- Small reviewable steps — no big code dumps
- Wait for input before generating large amounts of code
