# Katalogue documentation

Python tools for [Katalogue](https://katalogue.se), built on the Katalogue REST API.
There are two packages sharing one core:

| Package | Use it for |
|---------|------------|
| **`katalogue-cli`** | Interactive use and shell scripting from a terminal |
| **`katalogue-sdk`** | Scripts, notebooks, services, and agents in Python |

The CLI is a thin wrapper over the SDK — same authentication, same capabilities.

## Start here

- **[Getting started](getting-started.md)** — install, set up API access, and run your
  first command and first script.

## CLI

- [Command reference](cli/commands.md) — every resource, verb, flag, and the `auth` commands
- [Output formats and file output](cli/output-formats.md) — `--format`, `--output-file`, `--split-by`

## SDK

- [Client and authentication](sdk/client.md) — `KatalogueClient`, credentials, errors, token caching
- [Options and results](sdk/options.md) — everything `client.get()` can do

## Guides

- [Exporting hierarchies](guides/exporting.md) — pull a resource with its children and write files
- [Templates](guides/templates.md) — render dbt sources, column mappings, or your own Jinja2
- [Datatype conversion](guides/datatype-conversion.md) — map source types to Databricks, PySpark, …

## Reference

- [Filtering, selection, and sorting](reference/filtering.md) — shared by CLI and SDK
- [Resources](reference/resources.md) — hierarchy, default columns, field keys, response shape
- [Troubleshooting](reference/troubleshooting.md) — auth and configuration issues

## Maintainers

- [Publishing to PyPI](maintainers/publishing.md) — the release workflow

---

Source and issues: [github.com/kayentaconsulting/katalogue-python](https://github.com/kayentaconsulting/katalogue-python).
Contributions welcome — see [CONTRIBUTING.md](../CONTRIBUTING.md).
