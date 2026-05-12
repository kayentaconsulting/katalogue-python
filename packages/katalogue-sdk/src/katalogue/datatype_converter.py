"""Core datatype converter logic — apply source-to-target conversions to field dicts."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

_NON_ALNUM_RE = re.compile(r"[^0-9A-Za-z]+")


class DatatypeConverterConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = ""
    target: str = ""
    mappings: dict[str, str]

    @model_validator(mode="after")
    def _normalize_mappings(self) -> "DatatypeConverterConfig":
        self.mappings = normalize_datatype_mappings(self.mappings)
        return self


def normalize_datatype_name(value: str) -> str:
    """Return a canonical lookup key for a datatype name."""
    normalized = _NON_ALNUM_RE.sub("_", value.strip()).strip("_")
    return normalized.upper()


def normalize_datatype_mappings(mappings: dict[str, str]) -> dict[str, str]:
    """Normalize mapping keys and reject collisions after normalization."""
    normalized: dict[str, str] = {}
    originals: dict[str, str] = {}
    for key, value in mappings.items():
        canonical = normalize_datatype_name(key)
        previous = originals.get(canonical)
        if previous is not None and normalized[canonical] != value:
            raise ValueError(
                "Conflicting datatype converter keys normalize to "
                f"{canonical!r}: {previous!r} and {key!r}"
            )
        normalized[canonical] = value
        originals[canonical] = key
    return normalized


def _split_raw_type(raw_type: str) -> tuple[str, str]:
    stripped = raw_type.strip()
    base, sep, rest = stripped.partition("(")
    args = f"({rest}" if sep else ""
    return base.strip(), args


def apply_datatype_converter(raw_type: str, mappings: dict[str, str]) -> str:
    """Map a single raw database type string to its target platform equivalent.

    Rules without ``{args}`` discard precision (VARCHAR(255) → STRING).
    Rules with ``{args}`` preserve the parenthesised portion (DECIMAL(10,2) → DECIMAL(10,2)).
    Unknown types are returned unchanged.
    """
    base, args = _split_raw_type(raw_type)
    if not base:
        return raw_type
    canonical = normalize_datatype_name(base)
    target = mappings.get(canonical)
    if target is None:
        return raw_type
    return target.replace("{args}", args)


def enrich_fields_with_converted_datatype(
    fields: list[dict[str, Any]], config: DatatypeConverterConfig | None
) -> None:
    """Add ``datatype_converted`` to each field dict in-place.

    Fields without ``datatype_fullname`` or ``field_datatype`` are skipped.
    Passing ``config=None`` is a no-op.
    """
    if config is None:
        return
    for field in fields:
        raw = field.get("datatype_fullname") or field.get("field_datatype")
        if not isinstance(raw, str):
            continue
        field["datatype_converted"] = apply_datatype_converter(raw, config.mappings)
