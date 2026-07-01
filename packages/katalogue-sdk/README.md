# katalogue-sdk

Python client for [Katalogue](https://katalogue.se), built on the Katalogue REST API.
Standalone — no CLI or Click dependency — for use in scripts, notebooks, services,
and agents.

## Installation

```bash
pip install katalogue-sdk
# or with uv
uv add katalogue-sdk
```

## Quick start

```python
from katalogue import KatalogueClient, GetOptions

client = KatalogueClient()  # reads KATALOGUE_CLIENT_ID / _SECRET / _URL from the environment

# List all systems
result = client.get("system")
print(result.data)  # list of dicts

# All PII fields, selected columns, sorted
result = client.get("field", GetOptions(
    filters=["is_pii=true"],
    properties=["field_id", "field_name", "dataset_name"],
    sort=[{"field_name": "asc"}],
))
print(result.data)
```

Get API credentials by [creating an OAuth2 client in Katalogue](https://docs.katalogue.se/using-katalogue/katalogue_cli_and_sdk/#granting-access-to-katalogue).

## Documentation

Full documentation is published at
[kayentaconsulting.github.io/katalogue-python](https://kayentaconsulting.github.io/katalogue-python/):

- [Getting started](https://kayentaconsulting.github.io/katalogue-python/getting-started/)
- [Client and authentication](https://kayentaconsulting.github.io/katalogue-python/sdk/client/)
- [Options and results](https://kayentaconsulting.github.io/katalogue-python/sdk/options/)
- [Filtering and selection](https://kayentaconsulting.github.io/katalogue-python/reference/filtering/)
- [Templates](https://kayentaconsulting.github.io/katalogue-python/guides/templates/)
 · [Exporting](https://kayentaconsulting.github.io/katalogue-python/guides/exporting/)
 · [Datatype conversion](https://kayentaconsulting.github.io/katalogue-python/guides/datatype-conversion/)
