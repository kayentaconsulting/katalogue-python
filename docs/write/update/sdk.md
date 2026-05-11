# Updating catalog resources — SDK

See [common.md](common.md) for how the update mechanism works, file formats, updatable fields, and validation.

## Usage

```python
from katalogue import KatalogueClient, UpdateOptions

client = KatalogueClient()
```

### Single record

Pass `resource_id` and a `changes` dict with only the fields you want to overwrite:

```python
result = client.update(
    "business_term",
    UpdateOptions(resource_id=42, changes={"business_term_description": "New description"}),
)
print(result.ok, result.message)
print(result.data)   # list of updated records returned by the API
```

To clear a field, set its value to `None` in the `changes` dict:

```python
result = client.update(
    "business_term",
    UpdateOptions(resource_id=42, changes={"business_term_description": None}),
)
```

Omitting a key entirely leaves the server value unchanged. `None` is an explicit clear.

### Batch — in-memory records

Pass a list of dicts via `records`. Each dict must include the resource ID field; all other fields are optional:

```python
result = client.update(
    "business_term",
    UpdateOptions(records=[
        {"business_term_id": 42, "business_term_description": "A"},
        {"business_term_id": 43, "business_term_description": "B"},
    ]),
)
```

### Batch — from file

Use `load_records()` to parse a YAML, JSON, or CSV file, then pass the result to `UpdateOptions`:

```python
from katalogue import KatalogueClient, UpdateOptions, load_records

result = client.update(
    "business_term",
    UpdateOptions(records=load_records("changes.yml")),
)
```

`load_records()` dispatches on file extension (`.yml` / `.yaml`, `.json`, `.csv`) and raises `ValueError` for unsupported formats.

## Resources

| Resource string | ID field | Scope |
|---|---|---|
| `"business_term"` | `business_term_id` | `business_term.write` |
| `"field_description"` | `field_description_id` | `field_description.write` |
| `"glossary"` | `glossary_id` | `glossary.write` |

## `UpdateOptions` reference

| Field | Type | Default | Description |
|---|---|---|---|
| `resource_id` | `int \| str \| None` | `None` | ID of the record to update (single-record mode) |
| `changes` | `dict` | `{}` | Fields to overwrite (single-record mode) |
| `records` | `list[dict]` | `[]` | Batch records; each must include the resource ID field |
| `continue_on_error` | `bool` | `False` | Send one PUT per record; collect failures instead of raising |

`resource_id` + `changes` and `records` are mutually exclusive. Exactly one mode must be set.

## `WriteResult` reference

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `True` when all records were accepted |
| `message` | `str` | Human-readable status message from the API |
| `data` | `list[dict]` | Updated records returned by the API |
| `raw` | `Any \| None` | Raw API response envelope |
| `record_id` | `int \| str \| None` | Set on per-record results inside `partial_results` |
| `partial_results` | `list[WriteResult] \| None` | Populated when `continue_on_error=True`; one entry per record |

When `continue_on_error=True`, check `result.partial_results` to see which records succeeded and which failed:

```python
result = client.update(
    "business_term",
    UpdateOptions(records=load_records("changes.csv"), continue_on_error=True),
)
for r in result.partial_results:
    status = "OK" if r.ok else f"FAILED: {r.message}"
    print(f"id={r.record_id}: {status}")
```

## Error handling

```python
from katalogue import KatalogueClient, UpdateOptions, AuthError, ApiError

client = KatalogueClient()

try:
    result = client.update(
        "business_term",
        UpdateOptions(resource_id=42, changes={"business_term_description": "New"}),
    )
except ValueError as e:
    # Invalid resource name, missing ID, or validation failure
    print(f"Validation error: {e}")
except AuthError as e:
    # HTTP 401 — wrong credentials or revoked token
    print(f"Auth failed: {e}")
except ApiError as e:
    # HTTP 4xx/5xx — server rejected the request
    print(f"API error: {e}")
```
