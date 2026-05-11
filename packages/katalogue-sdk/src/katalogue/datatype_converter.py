"""Core type mapping — apply source-to-target datatype conversions to field dicts."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict

_TYPE_RE = re.compile(r"^(\w+)(\(.*\))?", re.IGNORECASE)


class DatatypeConverterConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = ""
    target: str = ""
    mappings: dict[str, str]


def apply_datatype_converter(raw_type: str, mappings: dict[str, str]) -> str:
    """Map a single raw database type string to its target platform equivalent.

    Rules without ``{args}`` discard precision (VARCHAR(255) → STRING).
    Rules with ``{args}`` preserve the parenthesised portion (DECIMAL(10,2) → DECIMAL(10,2)).
    Unknown types are returned unchanged.
    """
    match = _TYPE_RE.match(raw_type.strip())
    if not match:
        return raw_type
    base = match.group(1).upper()
    args = match.group(2) or ""
    upper_mappings = {k.upper(): v for k, v in mappings.items()}
    target = upper_mappings.get(base)
    if target is None:
        return raw_type
    return target.replace("{args}", args)


def enrich_fields_with_converted_datatype(
    fields: list[dict[str, Any]], config: DatatypeConverterConfig | None
) -> None:
    """Add ``datatype_converted`` to each field dict in-place.

    Fields without ``datatype_fullname`` are skipped. Passing ``config=None`` is a no-op.
    """
    if config is None:
        return
    for field in fields:
        raw = field.get("datatype_fullname")
        if raw is None:
            continue
        field["datatype_converted"] = apply_datatype_converter(raw, config.mappings)
