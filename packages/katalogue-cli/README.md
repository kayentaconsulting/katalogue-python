# katalogue-cli

Command-line interface for [Katalogue](https://katalogue.se), built on the Katalogue
REST API. A thin wrapper over [`katalogue-sdk`](https://pypi.org/project/katalogue-sdk/).

## Installation

```bash
pip install katalogue-cli
# or with uv
uv add katalogue-cli
```

## Quick start

```bash
# Store credentials once (client secret goes to your OS keychain)
katalogue auth login

# ...or use environment variables
export KATALOGUE_CLIENT_ID=...
export KATALOGUE_CLIENT_SECRET=...
export KATALOGUE_URL=https://your-instance.katalogue.se

# First call
katalogue system list
```

Get API credentials by [creating an OAuth2 client in Katalogue](https://docs.katalogue.se/using-katalogue/katalogue_cli_and_sdk/#granting-access-to-katalogue).

## Documentation

Full documentation lives in the repository:

- [Getting started](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/getting-started.md)
- [Command reference](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/cli/commands.md)
- [Output formats and file output](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/cli/output-formats.md)
- [Filtering and selection](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/reference/filtering.md)
- [Templates](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/guides/templates.md)
 · [Exporting](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/guides/exporting.md)
 · [Datatype conversion](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/guides/datatype-conversion.md)
- [Troubleshooting](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/reference/troubleshooting.md)
- [Documentation index](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/index.md)
