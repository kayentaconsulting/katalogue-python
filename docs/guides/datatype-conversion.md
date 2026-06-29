# Datatype Converter

Datatype conversion converts native source database types (e.g. `VARCHAR(255)` from SQL Server) to target platform types (e.g. `STRING` for Databricks, `StringType()` for PySpark). When active, every field record in hierarchical exports and direct field results gains a `datatype_converted` property.

## Contents

- [CLI usage](#cli-usage)
- [SDK usage](#sdk-usage)
- [Built-in mappings](#built-in-mappings)
- [Precision handling](#precision-handling)
- [Custom mapping files](#custom-mapping-files)
- [Registering custom mappings by name](#registering-custom-mappings-by-name)
- [Using datatype_converted in templates](#using-datatype_converted-in-templates)

## CLI usage

```bash
katalogue dataset get <id> --include-children --datatype-converter sqlserver-to-databricks --format json
katalogue datasource export <id> --datatype-converter postgres-to-databricks --template column-mapping
katalogue system export <id> --datatype-converter db2-to-pyspark --split-by dataset --output-dir ./out
```

`--datatype-converter` is available on all `get` and `export` commands.

## SDK usage

```python
from katalogue import KatalogueClient, GetOptions

result = client.get("system", GetOptions(
    resource_id=1,
    include_children=True,
    datatype_converter="sqlserver-to-databricks",
))
# Each field dict in result.data["fields"] now has "datatype_converted"
for field in result.data["fields"]:
    print(field["field_name"], field["datatype_fullname"], "->", field.get("datatype_converted"))

# The same conversion also applies to field get/list responses
field = client.get("field", GetOptions(resource_id=123, datatype_converter="sqlserver-to-databricks"))
print(field.data["datatype_converted"])
```

## Built-in mappings

| Name | Source | Target |
|------|--------|--------|
| `sqlserver-to-databricks` | SQL Server | Databricks SQL (`STRING`, `INT`, `TIMESTAMP_LTZ`, …) |
| `sqlserver-to-pyspark` | SQL Server | PySpark types (`StringType()`, `IntegerType()`, `TimestampType()`, …) |
| `db2-to-databricks` | IBM DB2 | Databricks SQL |
| `db2-to-pyspark` | IBM DB2 | PySpark types |
| `postgres-to-databricks` | PostgreSQL | Databricks SQL |
| `postgres-to-pyspark` | PostgreSQL | PySpark types |

### Timezone handling

Built-in mappings distinguish timezone-aware from timezone-naive source types:

| Source type | Databricks target | PySpark target |
|-------------|-------------------|----------------|
| `DATETIMEOFFSET` (SQL Server) | `TIMESTAMP_LTZ` | `TimestampType()` |
| `DATETIME`, `DATETIME2`, `SMALLDATETIME` | `TIMESTAMP_NTZ` | `TimestampNTZType()` |
| `TIMESTAMP` (DB2, standard) | `TIMESTAMP_NTZ` | `TimestampNTZType()` |
| `TIMESTAMPTZ` (PostgreSQL) | `TIMESTAMP_LTZ` | `TimestampType()` |
| `TIMESTAMP` (PostgreSQL) | `TIMESTAMP_NTZ` | `TimestampNTZType()` |

`TimestampNTZType()` requires Spark 3.4+. Override the built-in with a custom mapping if targeting an older cluster.

## Precision handling

Rules without `{args}` discard precision — `VARCHAR(255)` becomes `STRING`.

Rules containing `{args}` preserve the parenthesised portion:
- `DECIMAL(10,2)` → `DECIMAL(10,2)` (Databricks)
- `DECIMAL(10,2)` → `DecimalType(10,2)` (PySpark)

Lookup is case-insensitive, and spaces or repeated separators are normalized to underscores before matching. For example, `TIMESTAMP WITH TIME ZONE` and `TIMESTAMP_WITH_TIME_ZONE` resolve to the same rule.

Conflicting mapping keys that normalize to the same canonical name are rejected when the YAML file is loaded.

Unknown types pass through unchanged — if no rule matches, `datatype_converted` equals the original `datatype_fullname`.

## Custom mapping files

Mapping files are YAML with an optional header and a `mappings` table:

```yaml
source: oracle          # informational only
target: snowflake
mappings:
  VARCHAR2: VARCHAR
  NVARCHAR2: VARCHAR
  NUMBER: "NUMBER{args}"   # {args} → preserve precision: NUMBER(10,2) → NUMBER(10,2)
  DATE: TIMESTAMP_NTZ
  TIMESTAMP: TIMESTAMP_NTZ
  TIMESTAMP_WITH_TIME_ZONE: TIMESTAMP_LTZ
  CLOB: VARCHAR
  BLOB: BINARY
  RAW: BINARY
```

Use a direct path without registration:

```bash
katalogue dataset get <id> --include-children --datatype-converter ./mappings/oracle_snowflake.yaml
```

Direct `.yml` paths work too.

## Registering custom mappings by name

Register a mapping in `katalogue.toml` (or `[tool.katalogue.datatype_converters]` in `pyproject.toml`) so it can be referenced by name, just like templates:

**`katalogue.toml`:**

```toml
[datatype_converters.oracle-to-snowflake]
path = "datatype_converters/oracle_snowflake.yaml"

[datatype_converters.sqlserver-to-databricks]   # override the built-in
path = "datatype_converters/my_sqlserver.yaml"
```

**`pyproject.toml`:**

```toml
[tool.katalogue.datatype_converters.oracle-to-snowflake]
path = "datatype_converters/oracle_snowflake.yaml"
```

`path` is resolved relative to the config file's directory.

### Discovery order

For each directory from `cwd` up to the git root:

1. `katalogue.toml` — checked first
2. `pyproject.toml` — used if no `katalogue.toml` is found in that directory

Resolution priority for `--datatype-converter <value>`:

1. Repo-registered name (from the first config found above)
2. Built-in name
3. Direct `.yaml` / `.yml` file path

Repo-registered names always override built-ins with the same name.

## Using datatype_converted in templates

`datatype_converted` is available in Jinja2 templates via `f.datatype_converted`. Use `| default(...)` to fall back gracefully when no mapping is active:

```jinja2
type: {{ f.datatype_converted | default(f.datatype_fullname | default(f.field_datatype | default('unknown', true), true), true) }}
```

The built-in `column-mapping` and `dbt-source` templates already use this fallback chain.
