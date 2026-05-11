# Updating catalog resources — CLI

See [common.md](common.md) for how the update mechanism works, file formats, updatable fields, and validation.

## Commands

```bash
katalogue business-term update <id> [options]
katalogue field-description update <id> [options]
katalogue glossary update <id> [options]
```

## Single record — flag mode

Provide the record ID as a positional argument and pass only the fields you want to change as flags:

```bash
katalogue business-term update 42 --description "New description"
katalogue business-term update 42 --name "Updated Name" --definition "How it is calculated"

katalogue field-description update 7 --description "New text" --pii
katalogue field-description update 7 --no-pii

katalogue glossary update 3 --name "New Name" --description "New description"
```

To clear a field, pass `null`, `none`, or `NULL` as the value:

```bash
katalogue business-term update 42 --description null
katalogue glossary update 3 --description none
```

An empty string (`""`) is treated the same as not providing the flag — the server value is preserved.

## Batch — file mode

Pass a YAML, JSON, or CSV file with `--from-file`. Each record must include the resource ID; all other fields are optional:

```bash
katalogue business-term update --from-file changes.yml
katalogue field-description update --from-file fields.json
katalogue glossary update --from-file glossaries.csv
```

`--from-file` and a positional ID are mutually exclusive.

## Continue on error

By default, all records are sent in a single batch PUT — if the API rejects it, all records fail together. Use `--continue-on-error` to send one PUT per record and continue past individual failures:

```bash
katalogue business-term update --from-file changes.csv --continue-on-error
```

Output shows a per-record status line:

```
[OK  ] id=1: 1 Business Term updated
[OK  ] id=4: 1 Business Term updated
[FAIL] id=8: Failed to update business term(s)
```

Exit code is `1` if any record failed, `0` if all succeeded.

## Output

On success, the updated records are printed as JSON to stdout. Errors go to stderr; exit code is `1`.

## Flags per resource

### business-term update

| Flag | Field updated |
|---|---|
| `--name TEXT` | `business_term_name` |
| `--description TEXT` | `business_term_description` |
| `--definition TEXT` | `business_term_definition` |
| `--example TEXT` | `business_term_example` |

### field-description update

| Flag | Field updated |
|---|---|
| `--name TEXT` | `field_description_name` |
| `--description TEXT` | `field_description_description` |
| `--definition TEXT` | `field_description_definition` |
| `--example TEXT` | `field_description_example` |
| `--pii / --no-pii` | `is_pii` |

### glossary update

| Flag | Field updated |
|---|---|
| `--name TEXT` | `glossary_name` |
| `--description TEXT` | `glossary_description` |
