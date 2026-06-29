# CLI command reference

Every command follows the same shape:

```
katalogue [GLOBAL OPTIONS] <resource> <verb> [ARGS] [OPTIONS]
```

For authentication and your first command, start with the
[Getting started guide](../getting-started.md).

## Contents

- [Global options](#global-options)
- [Resources and verbs](#resources-and-verbs)
- [`list`](#list)
- [`get`](#get)
- [`export`](#export)
- [`keys`](#keys)
- [`auth`](#auth)
- [Exit codes](#exit-codes)

## Global options

These apply to every command and may be set as flags or environment variables.
Precedence is **flag > environment variable > config file > default**.

| Flag | Env var | Description |
|------|---------|-------------|
| `--client-id` | `KATALOGUE_CLIENT_ID` | OAuth2 client ID |
| `--client-secret` | `KATALOGUE_CLIENT_SECRET` | OAuth2 client secret (prefer the env var — flags appear in shell history) |
| `--base-url` | `KATALOGUE_URL` | API base URL (required) |
| `--token-url` | `KATALOGUE_TOKEN_URL` | OAuth2 token endpoint (defaults to `<base-url>/oidc/token`) |
| `--verbose` / `-v` | — | Show HTTP request details on stderr |
| `--version` | — | Show version and exit |

Credentials can also be stored once with [`katalogue auth login`](#auth) instead
of being passed on every call.

## Resources and verbs

The catalog is a hierarchy:

```
system → datasource → dataset-group → dataset → field
glossary   (independent)
```

| Resource | `list` | `get` | `export` | `keys` |
|----------|:------:|:-----:|:--------:|:------:|
| `system` | ✓ | ✓ | ✓ | ✓ |
| `datasource` | ✓ | ✓ | ✓ | ✓ |
| `dataset-group` | ✓ | ✓ | ✓ | ✓ |
| `dataset` | ✓ | ✓ | ✓ | ✓ |
| `field` | ✓ | ✓ | — | ✓ |
| `glossary` | ✓ | ✓ | ✓ | ✓ |

`field` has no `export` — use `katalogue dataset export <id>` to export a dataset
including all its fields.

## `list`

List all records of a resource type, optionally scoped to a parent.

```bash
katalogue system list
katalogue datasource list --system <id>
katalogue dataset-group list --datasource <id>
katalogue dataset list --dataset-group <id>
katalogue field list --dataset <id>
katalogue glossary list
```

Options:

| Option | Description |
|--------|-------------|
| `--filter` / `-w` | Filter expression; repeat for AND logic. See [Filtering](../reference/filtering.md) |
| `--properties` / `-p` | Comma-separated property names to include |
| `--wide` | Show all properties in table output |
| `--format` / `-f` | `json`, `yaml`, `yml`, `json-compact`, `compact`, `csv`, `table` (default: `table`) |
| parent flag | `--system`, `--datasource`, `--dataset-group`, or `--dataset` depending on the resource |

## `get`

Fetch and display a single record by ID.

```bash
katalogue system get 1
katalogue field get 42 --format yaml
katalogue datasource get 5 --include-children --format json
```

Options:

| Option | Description |
|--------|-------------|
| `--filter` / `-w` | Filter expression (applied to child records when `--include-children` is set) |
| `--properties` / `-p` | Comma-separated property names to include |
| `--format` / `-f` | `json`, `yaml`, `yml`, `json-compact`, `compact`, `csv`, `table` (default: `json`) |
| `--template` / `-t` | Render through a template. See [Templates](../guides/templates.md) |
| `--datatype-converter` | Convert source types. See [Datatype conversion](../guides/datatype-conversion.md) |
| `--include-children` | Fetch the resource and all descendants |
| `--output-file` / `-o` | Write rendered output to a file instead of stdout |
| `--output-dir` / `-d` | Directory for split output files |
| `--split-by` / `-s` | Split hierarchical output by resource level |
| `--filename-template` | Jinja2 expression used to name split files |
| `--overwrite` | Overwrite existing output files |
| `--dry-run` | Show planned output files without writing them |

File output, splitting, and templated rendering are covered in detail in the
[Exporting guide](../guides/exporting.md) and [Output formats](output-formats.md).

## `export`

Assemble a resource's full hierarchy and write it to a file. `export` always
fetches children — it is the convenient form of `get --include-children` aimed at
writing files. By default it writes `<resource>-<id>.json` to the current directory.

```bash
katalogue system export 1
katalogue datasource export 5 --template dbt-source
katalogue system export 1 --template dbt-source --split-by dataset --output-dir ./models
```

Options are the same file/template/datatype options as `get`, with these differences:

| Option | Description |
|--------|-------------|
| `--format` / `-f` | `json`, `yaml`, `yml`, `json-compact`, `compact`, `csv` (no `table`; default: `json`) |
| `--output-dir` / `-d` | Directory to write output files (default: `.`) |

Available for `system`, `datasource`, `dataset-group`, and `dataset` (and
`glossary`). See the [Exporting guide](../guides/exporting.md) for end-to-end recipes.

## `keys`

List the available field names for a resource — useful for discovering what to pass
to `--filter` and `--properties`. The keys come from a live API call, so they reflect
what the API actually returns for your instance.

```bash
katalogue field keys                 # one key per line
katalogue dataset keys --format json # JSON array
```

| Option | Description |
|--------|-------------|
| `--format` | `lines` (default) or `json` |

## `auth`

Store credentials once instead of passing them on every command. The client secret
is kept in your OS keychain (via [keyring](https://pypi.org/project/keyring/)); the
client ID, base URL, and token URL are written to a config file in your OS user
config directory (e.g. `~/.config/katalogue/config.toml` on Linux).

```bash
katalogue auth login     # prompts for any value not passed as a flag, then verifies
katalogue auth status    # show which credentials are set and where they come from
katalogue auth logout    # clear the token cache and remove the keychain entry
```

`auth login` accepts `--client-id`, `--client-secret`, `--base-url`, and
`--token-url`; it prompts for anything omitted. If no keychain backend is available,
set `KATALOGUE_CLIENT_SECRET` as an environment variable instead. See
[Troubleshooting](../reference/troubleshooting.md) for common auth issues.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | API error, auth error, or missing configuration |
| `2` | CLI usage error (bad arguments) |

Errors are written to stderr.
