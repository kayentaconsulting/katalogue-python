# Updating catalog resources — concepts

Katalogue supports updating `business_term`, `field_description`, and `glossary` records. Updates use **sparse input** — you only supply the fields you want to change, and the SDK fetches the current record to fill in the rest before writing.

## How it works

1. The SDK fetches each record's current state from the API.
2. Your changes are merged over the fetched record.
3. The merged records are sent to the API in a single batch PUT (default), or one PUT per record when `--continue-on-error` is set.

This means you never need to know internal required fields like `status_id` or `owner_principal_id` — those are preserved from the current record automatically.

Legacy rich-text (Draft.js JSON) stored in description fields is automatically converted to plain text during the merge step.

## File format reference

Batch updates can be supplied as YAML, JSON, or CSV. Each record must include the resource ID; all other fields are optional.

### YAML

```yaml
- business_term_id: 42
  business_term_description: "New description"
- business_term_id: 43
  business_term_name: "Updated Name"
  business_term_definition: "How it is calculated"
- business_term_id: 44
  business_term_description: null    # clears the field
```

Use `null`, `none`, `NULL`, or `None` to clear a field. Omitting the key leaves the server value unchanged.

### JSON

```json
[
  {"business_term_id": 42, "business_term_description": "New description"},
  {"business_term_id": 43, "business_term_name": "Updated Name"},
  {"business_term_id": 44, "business_term_description": null}
]
```

### CSV

```csv
business_term_id,business_term_description,business_term_definition
42,New description,
43,,How it is calculated
```

Row 42 updates description only; row 43 updates definition only. The blank cells are ignored entirely.

CSV values are always read as strings. The SDK coerces them to the correct types (integer IDs, booleans for `is_pii`, etc.) automatically.

**Empty cells are treated as "not provided"** — leaving a cell blank skips that field for that row, preserving the current value on the server. This lets different rows update different fields from the same CSV.

**To clear a field**, write `null`, `none`, `NULL`, or `None` (case-insensitive) in the cell:

```csv
business_term_id,business_term_description,business_term_example
42,null,New example
43,,
```

Row 42 clears the description and updates the example. Row 43 leaves both unchanged.

## Updatable fields per resource

### business_term

| Field | Type | Description |
|---|---|---|
| `business_term_name` | string | Name of the term |
| `business_term_description` | string | Short description |
| `business_term_definition` | string | How values are determined |
| `business_term_example` | string | Illustrative example |
| `business_term_type_id` | integer | Term type (internal ID) |
| `parent_business_term_id` | integer | Parent term for hierarchies |

### field_description

| Field | Type | Description |
|---|---|---|
| `field_description_name` | string | Name of the field description |
| `field_description_description` | string | Short description |
| `field_description_definition` | string | How values are determined |
| `field_description_example` | string | Illustrative example |
| `is_pii` | boolean | Whether the field contains PII |

### glossary

| Field | Type | Description |
|---|---|---|
| `glossary_name` | string | Name of the glossary |
| `glossary_description` | string | Description of the glossary |

## Input validation

All records in a file are validated before any API calls are made. If any record is invalid, the full list of errors is reported and nothing is written.

Example error output:

```
Validation failed:
  Row 2: 'business_term_id' — Field required
  Row 5: 'is_pii' — Input should be a valid boolean
```

## Error handling

| Situation | Behaviour |
|---|---|
| Invalid file format (not yml/json/csv) | `ValueError` before any API call |
| Missing ID field in a record | `ValueError` listing all invalid rows |
| API returns 400/5xx | `ApiError` with server message — entire batch fails |
| API returns 401 | `AuthError` |
| One record fails (`--continue-on-error`) | Other records are still attempted; exit code 1 if any failed |

---

- SDK usage: [sdk.md](sdk.md)
- CLI usage: [cli.md](cli.md)
