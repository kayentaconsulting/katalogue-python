# Katalogue CLI - Project Plan

## Status

| Milestone | Status |
|-----------|--------|
| M1: Foundation + `system get` | **DONE** — 21 tests passing |
| M2: Generic CRUD client | **DONE** — `list_resource`, `get_resource`, `list_by_parent` all implemented |
| M3: System + Datasource commands | **DONE** — list/get/children all implemented and tested |
| M4: Dataset group + Dataset + Field | **DONE** — list/get/children all implemented and tested |
| M5: Export + Task/Job commands | **Partial** — export system/glossary done; task/job not started |
| M6: Polish and Package | **DONE** — help text reviewed, README updated, `--version` done |

**Bonus (unplanned)**: `glossary list/get` implemented and tested.

---

## Purpose

Build a Python CLI for the Katalogue Data Catalog API that abstracts the raw API into an intuitive, user-friendly command-line experience. The CLI must work well for both human developers and AI agents.

## Target Users

- **Developers** who need to interact with Katalogue from the terminal or scripts
- **AI Agents** that need predictable, parseable command output and consistent exit codes

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Team standard |
| CLI framework | Click | Rich help text, composable groups, CliRunner for testing |
| HTTP / Auth | requests + requests-oauthlib | OAuth2 client credentials flow via `BackendApplicationClient` + `OAuth2Session` |
| Testing | pytest + requests-mock | Mocks requests at the session level |
| Packaging | uv + hatchling | Fast resolver, standard build backend |
| Entry point | `katalogue` | `pyproject.toml` `[project.scripts]` |

---

## API Surface

### Resource Hierarchy

```
system -> datasource -> dataset_group -> dataset -> field
```

### CRUD Endpoint Pattern

Every resource follows the same 3-endpoint pattern:

| Pattern | Purpose | Example |
|---------|---------|---------|
| `GET /api/<resource>/all` | List all rows | `GET /api/system/all` |
| `GET /api/<resource>/:id` | Get by primary key | `GET /api/system/abc123` |
| `GET /api/<resource>/<parent>/:parent_id` | Get children by parent | `GET /api/datasource/system/abc123` |

The parent-scoped endpoint does not exist for `system` (it has no parent).

### Full CRUD Endpoint Map

| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | GET | `/api/system/all` | List all systems |
| 2 | GET | `/api/system/:id` | Get system by ID |
| 3 | GET | `/api/datasource/all` | List all datasources |
| 4 | GET | `/api/datasource/:id` | Get datasource by ID |
| 5 | GET | `/api/datasource/system/:id` | List datasources for a system |
| 6 | GET | `/api/dataset_group/all` | List all dataset groups |
| 7 | GET | `/api/dataset_group/:id` | Get dataset group by ID |
| 8 | GET | `/api/dataset_group/datasource/:id` | List dataset groups for a datasource |
| 9 | GET | `/api/dataset/all` | List all datasets |
| 10 | GET | `/api/dataset/:id` | Get dataset by ID |
| 11 | GET | `/api/dataset/dataset_group/:id` | List datasets for a dataset group |
| 12 | GET | `/api/field/all` | List all fields |
| 13 | GET | `/api/field/:id` | Get field by ID |
| 14 | GET | `/api/field/dataset/:id` | List fields for a dataset |

### Export Endpoints (documented in OpenAPI spec)

| # | Method | Path | Purpose | Response Shape |
|---|--------|------|---------|----------------|
| 15 | GET | `/api/export/system/:id` | Export full system tree | `{meta: ExportHeader, data: ExportedSystem}` |
| 16 | GET | `/api/export/glossary/:id` | Export glossary entries | `{meta: ExportHeader, data: [ExportedGlossary]}` |

### Job/Task Endpoints (documented in OpenAPI spec)

| # | Method | Path | Purpose | Response Shape |
|---|--------|------|---------|----------------|
| 17 | POST | `/api/task/:id/run` | Trigger a task (creates a job) | `{ok, message, task, job}` |
| 18 | GET | `/api/job/task/:id` | List jobs for a task | Unspecified |

### Glossary

Glossary is a separate resource tree (not part of the system hierarchy). Endpoint patterns TBD - currently only the export endpoint is documented.

### Known Gaps

| Issue | Severity | Workaround |
|-------|----------|------------|
| CRUD endpoints not in OpenAPI spec (confirmed to exist) | Medium | Discover response shapes via API calls, use JSON passthrough |
| `ExportedSystem` schema nearly empty (`system: object`) | Medium | JSON passthrough, type later |
| Job list response has no schema | Medium | JSON passthrough |
| Auth is OAuth2 client credentials | Resolved | Uses `BackendApplicationClient` + `OAuth2Session`, auto-fetches/refreshes tokens, scope derived per operation (`<resource>.read`) |
| No pagination/filtering/sorting documented | Low | API doesn't offer it |
| Response shapes for CRUD endpoints unknown | Medium | Discover by calling the API, start with JSON passthrough |

---

## CLI Design

### Command Taxonomy (Resource-first)

Every resource in the hierarchy gets a Click group with consistent subcommands.

#### Core CRUD commands (system hierarchy)

```
# System (root resource - no parent)
katalogue system list                          # list all systems
katalogue system get <id>                      # get system by ID

# Datasource (parent: system)
katalogue datasource list                      # list all datasources
katalogue datasource get <id>                  # get datasource by ID
katalogue datasource list --system <id>        # list datasources for a system

# Dataset group (parent: datasource)
katalogue dataset-group list                   # list all dataset groups
katalogue dataset-group get <id>               # get dataset group by ID
katalogue dataset-group list --datasource <id> # list dataset groups for a datasource

# Dataset (parent: dataset_group)
katalogue dataset list                         # list all datasets
katalogue dataset get <id>                     # get dataset by ID
katalogue dataset list --dataset-group <id>    # list datasets for a dataset group

# Field (parent: dataset)
katalogue field list                           # list all fields
katalogue field get <id>                       # get field by ID
katalogue field list --dataset <id>            # list fields for a dataset
```

#### Navigation shortcut: children command

```
# "Show me what's under this resource" - follows the hierarchy
katalogue system children <id>                 # lists datasources for system <id>
katalogue datasource children <id>             # lists dataset groups for datasource <id>
katalogue dataset-group children <id>          # lists datasets for dataset group <id>
katalogue dataset children <id>                # lists fields for dataset <id>
```

This is syntactic sugar for the parent-scoped `list` command, but reads more naturally for hierarchy navigation.

#### Export commands

```
katalogue export system <id>                   # export full system tree (aggregated)
katalogue export glossary <id>                 # export glossary entries
```

Export is kept as its own group because it returns a different shape (meta + aggregated data) than CRUD `get` (single resource row). This distinction matters for users: `get` returns one row, `export` returns a tree/bundle.

#### Job/Task commands

```
katalogue task run <id>                        # trigger a task
katalogue task jobs <id>                       # list jobs for a task
```

### Global Flags

```
--token <token>             API token (or KATALOGUE_TOKEN env var)
--base-url <url>            API base URL (or KATALOGUE_URL env var)
--verbose / -v              Show request details on stderr
--no-color                  Disable color output (future)
```

### Per-Command Flags

```
--format json|table         Output format (default: json when piped, table on TTY)
```

For `list` commands with parent filtering:
```
--<parent> <id>             Filter by parent resource (e.g. --system <id>)
```

### Why This Taxonomy

1. **Resource-first** matches how users think about the data catalog hierarchy
2. **Consistent verbs**: every resource has `list` and `get`, the two operations users always need
3. **Parent filtering on `list`** via `--<parent> <id>` keeps the interface uniform rather than inventing a different command per parent relationship
4. **`children` shortcut** enables natural hierarchy navigation without remembering which child resource to query
5. **`export` stays separate** because it returns aggregated data with metadata, not a single row
6. **AI-friendly**: predictable `<resource> <verb> [<id>]` pattern; `--format json` always works
7. **Singular nouns** for all resource groups
8. **Hyphenated multi-word names**: `dataset-group` not `dataset_group` (CLI convention)

### Rejected Alternatives

- **Mirror the API paths** (`export system`, verb as path): exposes implementation detail
- **Verb-first** (`get system`, `list datasource`): less extensible, verb group grows unbounded
- **Nested subgroups** (`system datasource list`): too deep, hard to discover, Click doesn't nest well beyond 2 levels

### Design Conventions

| Area | Convention |
|------|-----------|
| Resource names | Singular, hyphenated (`dataset-group`, not `dataset_groups`) |
| Verbs | `list`, `get`, `children`, `run`, `export` |
| IDs | Positional arguments for the resource's own ID |
| Parent filtering | `--<parent> <id>` flag on `list` commands |
| Auth | OAuth2 client credentials: `--client-id` / `--client-secret` flags > `KATALOGUE_CLIENT_ID` / `KATALOGUE_CLIENT_SECRET` env vars |
| Base URL | `--base-url` flag > `KATALOGUE_URL` env var > default |
| Exit codes | 0 = success, 1 = user/API error, 2 = CLI usage error |
| Piped output | JSON by default (no colors, no progress) |
| TTY output | Table by default |
| Errors | Written to stderr, include what happened + what to do |
| Empty results | Exit 0, show empty table or `[]` in JSON |

---

## Architecture

### Package Structure

```
katalogue-cli/
  pyproject.toml
  PROJECT_PLAN.md              # this file
  first.md                     # original brief + OpenAPI spec
  .agents/                     # agent team definitions
  src/
    katalogue/
      cli/
        main.py                # Click root group, global options
        system.py              # system list, get, children
        datasource.py          # datasource list, get, children
        dataset_group.py       # dataset-group list, get, children
        dataset.py             # dataset list, get, children
        field.py               # field list, get
        export.py              # export system, export glossary
        task.py                # task run, task jobs
      client/
        api.py                 # KatalogueClient (httpx), AuthError, ApiError
      config/
        settings.py            # resolve_settings() - token, base_url
      formatters/
        output.py              # format_json, format_table
  tests/
    conftest.py                # shared fixtures
    test_cli_system.py         # CLI tests for system commands
    test_cli_datasource.py
    test_cli_dataset_group.py
    test_cli_dataset.py
    test_cli_field.py
    test_cli_export.py
    test_cli_task.py
    test_client.py             # HTTP client unit tests (respx)
    test_config.py             # config resolution tests
    test_formatters.py         # formatter tests
    fixtures/                  # sample API responses
      ...
```

### Layer Responsibilities

| Layer | Does | Does Not |
|-------|------|----------|
| `cli/` | Parse args, call client, format output, handle errors | Construct URLs, manage HTTP, contain business logic |
| `client/` | Make HTTP requests, parse responses, raise typed errors | Format output, know about Click, read config |
| `config/` | Resolve token/URL from flags, env vars, defaults | Make HTTP calls, format output |
| `formatters/` | Turn data dicts into strings (JSON, table, YAML) | Know about HTTP, Click, or config |

### Key Design Decisions

1. **Generic client methods** - The CRUD pattern is uniform, so the client can use generic `list_resource()`, `get_resource()`, and `list_by_parent()` methods instead of one method per endpoint. This avoids 14 near-identical methods.
2. **No service layer** - CLI commands call the client directly. Revisit when multi-step workflows emerge (e.g., "run task and poll until done").
3. **src layout** - `src/katalogue/` prevents accidental imports from the working directory.
4. **Typed exceptions** - `AuthError` and `ApiError` allow CLI to produce specific error messages without inspecting HTTP details.
5. **Config as a dataclass** - `Settings(token, base_url)` is frozen and passed through Click context.
6. **One CLI file per resource** - Each resource gets its own file with `list`, `get`, and optionally `children` commands. Keeps files small and focused.

---

## Agent Team

Six conceptual agents used as an internal structured working model to ensure quality across all dimensions. They are not separate chat participants - they represent perspectives consulted during each feature slice.

| Agent | Role | Question They Answer |
|-------|------|---------------------|
| **Atlas** | API Cartographer | What does the API actually do? |
| **Mira** | CLI UX Architect | What should the user experience? |
| **Kai** | Click/Python Architect | How should the code be structured? |
| **Vera** | Test Strategist | What tests prove this works? |
| **Reed** | Refactoring Guardian | Is this still clean? |
| **Dana** | Delivery/DX Reviewer | Is this actually done? |

### Per-Slice Workflow

```
Atlas maps endpoints
  -> Mira designs command UX
    -> Kai proposes structure
      -> Vera writes test plan
        -> Implement (TDD: RED -> GREEN -> REFACTOR)
          -> Reed reviews layering
            -> Dana reviews UX and declares done/not done
```

### Conflict Resolution

- UX trumps architectural purity
- Simplicity trumps completeness
- Layers must be justified by current complexity, not future hypotheticals

Full agent definitions: `.agents/<name>.md`

---

## TDD Workflow

Every feature slice follows this cycle:

### 1. Discovery
- Summarize the feature
- Map the relevant endpoints from the spec (Atlas)
- Identify uncertainties and assumptions
- Propose the command UX (Mira)

### 2. Plan
- List files to create/change (Kai)
- Define acceptance criteria
- Write the test plan: test names + descriptions (Vera)

### 3. TDD
- Write all tests first (RED - all fail)
- Implement layer by layer until tests pass (GREEN)
- Refactor: naming, help text, error messages

### 4. Review
- Review layering and coupling (Reed)
- Review help text, error messages, UX (Dana)
- Declare done or list what's missing
- Propose next slice

### Testing Standards

- **pytest** with Click `CliRunner` for CLI integration tests
- **respx** for mocking httpx at the HTTP layer
- **Behavior over implementation**: test what the user sees, not mock call counts
- **Coverage targets**: happy path, auth failure, API errors (400/500), missing config, empty results, output format contract

---

## Milestones

### Milestone 1: Foundation + `system get` [DONE]

**Scope**: Project scaffolding, pyproject.toml, config, client, formatters, `system get` command, full tests.

**Status**: Complete. 21 tests passing.

**What was delivered**:
- `katalogue system get <id> --format json|table`
- Global `--token`, `--base-url`, `--verbose` flags
- Config resolution (CLI flag > env var > default)
- HTTP client with `AuthError`/`ApiError`
- JSON and table formatters
- Full test coverage across all 4 layers

**Note**: The current `system get` calls the export endpoint. This will be refactored in Milestone 3 to call the CRUD endpoint instead, and the export will move to `katalogue export system`.

### Milestone 2: Generic CRUD client [NEXT]

**Scope**: Refactor the HTTP client to support the uniform CRUD pattern. Add generic `list_resource()`, `get_resource()`, and `list_by_parent()` methods. This is the foundation for all 5 resource commands.

**Acceptance criteria**:
- `client.list_resource("system")` calls `GET /api/system/all`
- `client.get_resource("system", "abc123")` calls `GET /api/system/abc123`
- `client.list_by_parent("datasource", "system", "abc123")` calls `GET /api/datasource/system/abc123`
- All error handling (401, 400, 500) works uniformly
- Auth header sent on all requests
- Existing tests still pass

### Milestone 3: System + Datasource commands

**Scope**: Implement `system` and `datasource` command groups using the generic client. Refactor existing `system get` to use CRUD endpoint. Move export to its own group.

**Commands delivered**:
```
katalogue system list
katalogue system get <id>
katalogue system children <id>          # alias for datasource list --system <id>
katalogue datasource list [--system <id>]
katalogue datasource get <id>
katalogue datasource children <id>      # alias for dataset-group list --datasource <id>
```

**Acceptance criteria**:
- All commands work with `--format json|table`
- `system children` and `datasource list --system` return the same data
- Empty results handled gracefully
- Table formatter shows useful columns for each resource

### Milestone 4: Dataset group + Dataset + Field commands

**Scope**: Complete the hierarchy with the remaining 3 resources. Same pattern as Milestone 3.

**Commands delivered**:
```
katalogue dataset-group list [--datasource <id>]
katalogue dataset-group get <id>
katalogue dataset-group children <id>
katalogue dataset list [--dataset-group <id>]
katalogue dataset get <id>
katalogue dataset children <id>
katalogue field list [--dataset <id>]
katalogue field get <id>
```

### Milestone 5: Export + Task/Job commands

**Scope**: Export endpoints (aggregated tree data) and task/job workflow.

**Commands delivered**:
```
katalogue export system <id>
katalogue export glossary <id>
katalogue task run <id>
katalogue task jobs <id>
```

**Acceptance criteria**:
- Export returns aggregated data with metadata header
- `task run` sends POST, shows result
- `task jobs` lists job history
- Consider `task run <id> --wait` (poll until done)

### Milestone 6: Polish and Package

**Scope**: Make the CLI installable and usable by someone who hasn't read the source.

**Acceptance criteria**:
- `--version` flag
- README with install + quickstart + full command reference
- All help text reviewed
- All error messages reviewed
- `uv tool install katalogue-cli` works
- Config file support (`~/.config/katalogue/config.toml`) if warranted

### Future Milestones (out of scope for v0.1.0)

- `katalogue system tree <id>` - ASCII tree of the full hierarchy
- Shell completions
- `--output` flag to write to file
- YAML output format
- Glossary CRUD commands (when endpoints are documented)

---

## Verification Checklist

Applied after each milestone:

- [ ] `uv run pytest` - all tests green
- [ ] `katalogue --help` - clear, complete
- [ ] `katalogue <group> --help` - clear, complete
- [ ] `katalogue <group> <command> --help` - clear, complete
- [ ] `katalogue <command> --format json | python -m json.tool` - valid JSON
- [ ] Missing token - actionable error message, exit code 1
- [ ] Invalid token (401) - actionable error message, exit code 1
- [ ] Bad request (400) - error from API shown, exit code 1
- [ ] Piped output - no color codes, no progress indicators
- [ ] All previous tests still pass (no regressions)

---

## Working Style

- **Be opinionated**: push back on weak design choices
- **Small steps**: one command per milestone, tests before code
- **No big dumps**: implement incrementally, review at each step
- **Wait for input**: don't generate large amounts of code without approval
- **Spec is input, not gospel**: optimize CLI UX over spec fidelity
- **Agent team is a lens**: use the 6 perspectives, present one recommendation
