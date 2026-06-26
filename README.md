# Katalogue

Monorepo with Python utility tools for [Katalogue](https://katalogue.se). These tools build upon the Katalogue REST API. Contains two packages:

| Package | Description | When to use |
|---------|-------------|-------------|
| [`katalogue-sdk`](packages/katalogue-sdk/README.md) | Standalone HTTP client + OAuth2 | Scripts, notebooks, agents, services |
| [`katalogue-cli`](packages/katalogue-cli/README.md) | Click CLI wrapping the SDK | Interactive use, shell scripting |

The SDK has no Click dependency and can be used in any Python environment. The CLI is a thin consumer of the SDK.

## Installation

```bash
# CLI (includes the SDK as a dependency)
pip install katalogue-cli

# SDK only (for use in scripts, notebooks, and services)
pip install katalogue-sdk
```

## Development

```bash
uv sync                    # install all workspace dependencies
uv run pytest              # run all tests (both packages)
uv run pytest packages/katalogue-sdk/tests   # SDK only
uv run pytest packages/katalogue-cli/tests   # CLI only
uv run katalogue --help    # smoke test the CLI entry point
```

## Package docs

- [katalogue-sdk](packages/katalogue-sdk/README.md) — installation, credentials, client methods, error handling
- [katalogue-cli](packages/katalogue-cli/README.md) — commands, filtering, output formats, global flags

## Usage

### Setup Katalog API Access
The SDK (which is also used by the CLI) requires the Katalogue REST API to be enabled and a Katalogue OIDC client with necessary scopes.

[Grant Access to Katalogue](https://docs.katalogue.se/using-katalogue/katalogue_cli_and_sdk/#granting-access-to-katalogue)