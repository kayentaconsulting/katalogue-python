import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

FilterOperator = Literal["=", "!=", ">", ">=", "<", "<=", "in", "not-in", "contains"]

# Word operators must appear surrounded by whitespace.
_WORD_OP_RE = re.compile(r"^([\w.]+)\s+(not-in|in|contains)\s+(.+)$")
# Symbol operators: longest first to avoid e.g. '!' consuming before '!='.
_SYMBOL_OP_RE = re.compile(r"^([\w.]+)\s*(!=|>=|<=|>|<|=)\s*(.*)$")


class Filter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str = Field(min_length=1)
    operator: FilterOperator
    value: Any


def _coerce_value(raw: str) -> bool | int | str:
    """Coerce an unquoted token to bool, int, or str."""
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        return raw


def _strip_quotes(s: str) -> tuple[str, bool]:
    """Return (stripped, was_quoted). Strips matching outer quotes."""
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1], True
    return s, False


class FilterParser:
    def parse(
        self, value: "str | list[str] | list[Filter] | None"
    ) -> "list[Filter] | None":
        if value is None:
            return None
        if isinstance(value, list):
            if not value:
                return []
            # Pass-through if already Filter objects
            if isinstance(value[0], Filter):
                return [Filter.model_validate(f.model_dump()) for f in value]  # type: ignore[union-attr]
            return [self._parse_one(s) for s in value]  # type: ignore[arg-type]
        return [self._parse_one(value)]

    def _parse_one(self, s: str) -> Filter:
        if not s.strip():
            raise ValueError("empty filter string")

        # Try word operators first
        m = _WORD_OP_RE.match(s)
        if m:
            path, op, raw_value = m.group(1), m.group(2), m.group(3).strip()
            if op in ("in", "not-in"):
                parts = [p.strip() for p in raw_value.split(",")]
                coerced: Any = [_coerce_value(p) for p in parts]
            else:
                stripped, quoted = _strip_quotes(raw_value)
                coerced = stripped if quoted else _coerce_value(raw_value)
            return Filter(path=path, operator=op, value=coerced)  # type: ignore[arg-type]

        # Try symbol operators
        m = _SYMBOL_OP_RE.match(s)
        if m:
            path, op, raw_value = m.group(1), m.group(2), m.group(3)
            if not path:
                raise ValueError(f"empty path in filter: {s!r}")
            if not raw_value and raw_value == "":
                raise ValueError(f"empty value in filter: {s!r}")
            stripped, quoted = _strip_quotes(raw_value)
            coerced = stripped if quoted else _coerce_value(raw_value)
            return Filter(path=path, operator=op, value=coerced)  # type: ignore[arg-type]

        # No operator matched — check for common error patterns
        if s.startswith("="):
            raise ValueError(f"empty path in filter: {s!r}")
        raise ValueError(f"no valid operator found in filter: {s!r}")


def parse_filters(
    value: "str | list[str] | list[Filter] | None",
) -> "list[Filter] | None":
    return FilterParser().parse(value)


def _str_eq(a: Any, b: Any) -> bool:
    """Case-insensitive equality for strings; exact equality otherwise."""
    if isinstance(a, str) and isinstance(b, str):
        return a.lower() == b.lower()
    return a == b


def apply_filter(row: "dict[str, Any]", f: Filter) -> bool:
    """Return True if row satisfies filter f.

    Path interpretation:
    - Dotted path (e.g. "attrs.code"): performs any/all lookup against a nested list.
    - Plain key: direct row lookup with field_* prefix fallback.
    """
    key = f.path
    op = f.operator
    value = f.value

    # Dotted path → nested-list lookup
    if "." in key:
        container, subkey = key.split(".", 1)
        items = row.get(container)
        if isinstance(items, list):
            if op == "=":
                return any(_str_eq(item.get(subkey), value) for item in items)
            if op == "!=":
                return all(not _str_eq(item.get(subkey), value) for item in items)
            if op == "contains":
                return any(
                    isinstance(item.get(subkey), str)
                    and isinstance(value, str)
                    and value.lower() in item.get(subkey, "").lower()
                    for item in items
                )
            if op == "in":
                lst = value if isinstance(value, list) else [value]
                return any(
                    any(_str_eq(item.get(subkey), v) for v in lst) for item in items
                )
            if op == "not-in":
                lst = value if isinstance(value, list) else [value]
                return all(
                    not any(_str_eq(item.get(subkey), v) for v in lst) for item in items
                )
        # No list or absent key: only != is truthy
        return op in ("!=", "not-in")

    # Plain key lookup with field_* fallback
    current = row.get(key)
    if current is None:
        current = row.get(f"field_{key}")

    if op == "=":
        return _str_eq(current, value)
    if op == "!=":
        return not _str_eq(current, value)
    if op == ">":
        return current is not None and current > value  # type: ignore[operator]
    if op == ">=":
        return current is not None and current >= value  # type: ignore[operator]
    if op == "<":
        return current is not None and current < value  # type: ignore[operator]
    if op == "<=":
        return current is not None and current <= value  # type: ignore[operator]
    if op == "in":
        lst = value if isinstance(value, list) else [value]
        return any(_str_eq(current, v) for v in lst)
    if op == "not-in":
        lst = value if isinstance(value, list) else [value]
        return not any(_str_eq(current, v) for v in lst)
    if op == "contains":
        return (
            isinstance(current, str)
            and isinstance(value, str)
            and value.lower() in current.lower()
        )
    return False
