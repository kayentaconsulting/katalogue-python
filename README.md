# Katalogue

Monorepo with Python tools for [Katalogue](https://katalogue.se), built on the
Katalogue REST API. Two packages share one core:

| Package | Description | When to use |
|---------|-------------|-------------|
| [`katalogue-sdk`](packages/katalogue-sdk/README.md) | Standalone HTTP client + OAuth2 | Scripts, notebooks, agents, services |
| [`katalogue-cli`](packages/katalogue-cli/README.md) | Click CLI wrapping the SDK | Interactive use, shell scripting |

The SDK has no Click dependency and runs in any Python environment. The CLI is a thin
consumer of the SDK.

## Documentation

**📖 Full documentation: [docs/index.md](docs/index.md)**

- [Getting started](docs/getting-started.md) — install, API access, first command and script
- [CLI command reference](docs/cli/commands.md)
- [SDK client](docs/sdk/client.md) and [options](docs/sdk/options.md)
- [Templates](docs/guides/templates.md), [exporting](docs/guides/exporting.md),
  [datatype conversion](docs/guides/datatype-conversion.md)
- [Troubleshooting](docs/reference/troubleshooting.md)

## Installation

```bash
# CLI (includes the SDK as a dependency)
pip install katalogue-cli

# SDK only (for use in scripts, notebooks, and services)
pip install katalogue-sdk
```

| Package | PyPI |
|---------|------|
| `katalogue-cli` | [pypi.org/project/katalogue-cli](https://pypi.org/project/katalogue-cli/) |
| `katalogue-sdk` | [pypi.org/project/katalogue-sdk](https://pypi.org/project/katalogue-sdk/) |

## Setup: Katalogue API access

The SDK and CLI require the Katalogue REST API to be enabled and an OIDC client with
the necessary scopes. See
[Grant access to Katalogue](https://docs.katalogue.se/using-katalogue/katalogue_cli_and_sdk/#granting-access-to-katalogue),
then follow [Getting started](docs/getting-started.md).

## Development

```bash
uv sync                                      # install all workspace dependencies
uv run pytest                                # run all tests (both packages)
uv run pytest packages/katalogue-sdk/tests   # SDK only
uv run pytest packages/katalogue-cli/tests   # CLI only
uv run katalogue --help                      # smoke test the CLI entry point
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow and
[docs/maintainers/publishing.md](docs/maintainers/publishing.md) for releases.
