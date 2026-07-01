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

Full documentation is published at
[kayentaconsulting.github.io/katalogue-python](https://kayentaconsulting.github.io/katalogue-python/):

- [Getting started](https://kayentaconsulting.github.io/katalogue-python/getting-started/)
- [Command reference](https://kayentaconsulting.github.io/katalogue-python/cli/commands/)
- [Output formats and file output](https://kayentaconsulting.github.io/katalogue-python/cli/output-formats/)
- [Filtering and selection](https://kayentaconsulting.github.io/katalogue-python/reference/filtering/)
- [Templates](https://kayentaconsulting.github.io/katalogue-python/guides/templates/)
 · [Exporting](https://kayentaconsulting.github.io/katalogue-python/guides/exporting/)
 · [Datatype conversion](https://kayentaconsulting.github.io/katalogue-python/guides/datatype-conversion/)
- [Troubleshooting](https://kayentaconsulting.github.io/katalogue-python/reference/troubleshooting/)
