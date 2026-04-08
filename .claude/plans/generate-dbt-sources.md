# Plan: `generate dbt-sources` command

## Context

Users want to generate dbt `sources.yml` files from catalog data. Katalogue's resource hierarchy (datasource → dataset_group → dataset → field) maps cleanly to the dbt sources structure. This is a new `generate` command group, distinct from `export` (which mirrors API endpoints) — `generate` produces files in third-party formats.

---

## CLI Interface

```
katalogue generate dbt-sources [OPTIONS]

Options:
  --datasource-id TEXT     Katalogue datasource ID. (required)
  --dataset-group-id TEXT  Limit output to a single dataset_group ID (optional).
  --split                  Emit one YAML document per dataset_group instead of one combined file.
  --output PATH            Write output here. Without --split: file path. With --split: directory path.
  --help
```

No `--format` option — the command produces YAML exclusively.

### Output modes

**Default (combined):** One YAML file with one `sources` block per dataset_group, all in a single document. Stdout or `--output <file>`.

**Single schema (`--dataset-group-id <id>`):** Fetch only that one dataset_group (skips the group-list call, directly fetches datasets for that group). Produces a single-block combined YAML. Can be combined with `--output <file>`.

**Split (`--split`):** One YAML document per dataset_group. To stdout, each document is separated by `---`. With `--output <dir>`, each document is written to `<dir>/_source__{datasource_name}__{dataset_group_name}.yml`. The directory is created if it does not exist.

Note: `--dataset-group-id` and `--split` are mutually exclusive — splitting a single group is identical to combined output.

Example output (`katalogue generate dbt-sources --datasource-id ds-001`):

```yaml
version: 2

sources:
  - name: my_postgres__public
    schema: public
    tables:
      - name: users
        columns:
          - name: user_id
            meta:
              pii: false
          - name: email
            description: User email address
            meta:
              pii: true

  - name: my_postgres__reporting
    schema: reporting
    tables:
      - name: revenue_summary
        columns:
          - name: amount
            meta:
              pii: false
```

**Schema grouping:** one `sources` block per `dataset_group`. Source name = `{datasource_name}__{dataset_group_name}`. This is always correct — a single block with mixed schemas would break dbt.

**Descriptions:** Every resource level carries a `description` field. These map directly to dbt:
- `datasource.description` → source block `description`
- `dataset_group.description` → omitted (dbt has no schema-level description)
- `dataset.description` → table `description`
- `field.description` → column `description`

Omit `description` key when value is null/empty — don't render `description: null`.

No glossary integration in v1 — all description text comes from native resource fields. Glossary enrichment can be added later if there's a clear use case.

---

## Data Fetching (ordered API calls)

```
1. get_resource("datasource", datasource_id)            → {datasource_name, description, ...}
2a. (default) list_by_parent("dataset_group", "datasource", id) → [{dataset_group_id, dataset_group_name, description}, ...]
2b. (--dataset-group-id) get_resource("dataset_group", dataset_group_id) → {dataset_group_id, dataset_group_name, description}
    wrap in a list so the rest of the logic is identical
3. For each group:
   list_by_parent("dataset", "dataset_group", grp_id)  → [{dataset_id, dataset_name, description}, ...]
4. For each dataset:
   list_by_parent("field", "dataset", ds_id)           → [{field_id, field_name, is_pii, description}, ...]
```

Use `_fetch_or_exit(ctx, call)` from `common.py` for each call — returns `None` on error and the handler returns early.

**Intermediate structure** assembled in the CLI handler before passing to the formatter:

```python
{
    "datasource_name": "my_postgres",
    "datasource_description": "Main production database",   # may be None
    "groups": [
        {
            "dataset_group_name": "public",
            "datasets": [
                {
                    "dataset_name": "users",
                    "dataset_description": "Core user records",   # may be None
                    "fields": [
                        {"field_name": "user_id", "is_pii": False, "description": "Primary key"},  # may be None
                    ]
                }
            ]
        }
    ]
}
```

---

## Implementation Steps

### 1. `pyproject.toml`

Add `"pyyaml>=6.0"` to `[project.dependencies]`. Run `uv sync`.

### 2. `src/katalogue/formatters/dbt.py` (new file)

Three pure functions — no Click, no HTTP:

```python
def build_dbt_sources(data: dict) -> dict:
    """Assemble pyyaml-ready dict (combined: all groups in one sources list)."""

def format_dbt_sources(data: dict) -> str:
    """Return single YAML string for all groups."""

def format_dbt_sources_split(data: dict) -> list[tuple[str, str]]:
    """Return list of (filename_stem, yaml_str) — one entry per dataset_group.
    Filename stem = _source__{datasource_name}__{dataset_group_name}
    Caller appends .yml when writing to disk."""
```

pyyaml renders Python `True`/`False` as `true`/`false` — correct dbt YAML. Omit `description` key from column dict when value is falsy.

### 3. `src/katalogue/cli/generate.py` (new file)

```python
@click.group()
def generate() -> None:
    """Generate configuration files from catalog data."""

@generate.command("dbt-sources")
@click.option("--datasource-id", required=True, help="Katalogue datasource ID.")
@click.option("--dataset-group-id", default=None, help="Limit to a single dataset group ID.")
@click.option("--split", is_flag=True, default=False, help="Emit one YAML document per schema instead of one combined file.")
@click.option("--output", "output_path", default=None, type=click.Path(), help="File path (default) or directory path (--split).")
@click.pass_context
def dbt_sources(ctx, datasource_id, dataset_group_id, split, output_path):
    """Generate a dbt sources.yml for a datasource."""
    ...
```

Handler logic:
- Fetch all data via `_fetch_or_exit` throughout
- Build intermediate structure
- Without `--split`: call `format_dbt_sources(data)` → single YAML string → stdout or `--output <file>`
- With `--split`: call `format_dbt_sources_split(data)` → `list[tuple[str, str]]` of `(stem, yaml_str)` pairs
  - Without `--output`: print each document to stdout separated by `---\n`
  - With `--output <dir>`: `os.makedirs(dir, exist_ok=True)`, write each to `<dir>/<stem>.yml`, echo confirmations to stderr

### 4. `src/katalogue/cli/main.py`

Add:
```python
from katalogue.cli.generate import generate
cli.add_command(generate)
```

### 5. `tests/test_formatters_dbt.py` (new file, ~22 tests)

Pure unit tests — no mocking. Cover: version=2, source naming (`datasource__schema`), one block per group, table/column structure, `meta.pii` true/false, description at source/table/column levels (present/absent/null), empty groups/datasets/fields, valid YAML output. For split: correct number of entries returned, each is individually valid YAML, filename stems match `_source__{datasource}__{group}` pattern.

### 6. `tests/test_cli_generate.py` (new file, ~25 tests)

Uses `runner`/`cli_auth`/`mock_client` fixtures from `conftest.py`. Classes:
- `TestGenerateDbtSourcesHappyPath` — exit code 0, valid YAML, correct API calls made
- `TestGenerateDbtSourcesOutputFile` — `--output` writes file, nothing on stdout
- `TestGenerateDbtSourcesSplit` — `--split` stdout has `---` separator, `--split --output <dir>` writes multiple files with correct names
- `TestGenerateDbtSourcesDatasetGroup` — `--dataset-group-id` fetches that group directly (not group list), produces single-block output; error if combined with `--split`
- `TestGenerateDbtSourcesErrors` — auth error, API error on each fetch level
- `TestGenerateDbtSourcesEdgeCases` — empty groups, empty datasets, empty fields

---

## Critical Files

| File | Change |
|------|--------|
| `pyproject.toml` | Add `pyyaml>=6.0` dependency |
| `src/katalogue/formatters/dbt.py` | New — `build_dbt_sources`, `format_dbt_sources`, `format_dbt_sources_split` |
| `src/katalogue/cli/generate.py` | New — `generate` group + `dbt-sources` command |
| `src/katalogue/cli/main.py` | Import and register `generate` group |
| `tests/test_formatters_dbt.py` | New — ~22 formatter unit tests |
| `tests/test_cli_generate.py` | New — ~25 CLI integration tests |

No changes needed to `client/api.py`, `common.py`, or `formatters/output.py`.

---

## TDD Sequence

1. Add `pyyaml` to `pyproject.toml` → `uv sync`
2. Write `tests/test_formatters_dbt.py` → RED
3. Implement `src/katalogue/formatters/dbt.py` → GREEN
4. Write `tests/test_cli_generate.py` → RED
5. Implement `src/katalogue/cli/generate.py` → GREEN
6. Register in `main.py`
7. `uv run pytest --tb=short -q` — all ~170 tests pass

---

## Verification

```bash
uv run pytest --tb=short -q
uv run katalogue generate --help
uv run katalogue generate dbt-sources --help
# Live test (requires real credentials):
uv run katalogue generate dbt-sources --datasource-id <id>
uv run katalogue generate dbt-sources --datasource-id <id> --output sources.yml
uv run katalogue generate dbt-sources --datasource-id <id> --split
uv run katalogue generate dbt-sources --datasource-id <id> --split --output ./dbt_sources/
uv run katalogue generate dbt-sources --datasource-id <id> --dataset-group-id <id>
uv run katalogue generate dbt-sources --datasource-id <id> --dataset-group-id <id> --output sources.yml
```
