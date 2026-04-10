# katalogue

Python monorepo for the [Katalogue](https://katalogue.se) Data Catalog API. Contains two packages:

| Package | Description | When to use |
|---------|-------------|-------------|
| [`katalogue-sdk`](packages/katalogue-sdk/README.md) | Standalone HTTP client + OAuth2 | Scripts, notebooks, agents, services |
| [`katalogue-cli`](packages/katalogue-cli/README.md) | Click CLI wrapping the SDK | Interactive use, shell scripting |

The SDK has no Click dependency and can be used in any Python environment. The CLI is a thin consumer of the SDK.

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
