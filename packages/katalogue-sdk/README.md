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

Full documentation lives in the repository:

- [Getting started](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/getting-started.md)
- [Client and authentication](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/sdk/client.md)
- [Options and results](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/sdk/options.md)
- [Filtering and selection](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/reference/filtering.md)
- [Templates](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/guides/templates.md)
 · [Exporting](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/guides/exporting.md)
 · [Datatype conversion](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/guides/datatype-conversion.md)
- [Documentation index](https://github.com/kayentaconsulting/katalogue-python/blob/main/docs/index.md)
