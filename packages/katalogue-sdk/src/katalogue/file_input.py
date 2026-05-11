"""Parse YAML, JSON, or CSV input files into a list of dicts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

_NULL_SENTINELS = frozenset({"null", "none"})


def _null_if_sentinel(v: Any) -> Any:
    """Convert empty string or null-sentinel strings (null/none, any case) to None."""
    if isinstance(v, str) and (v == "" or v.lower() in _NULL_SENTINELS):
        return None
    return v


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {k: _null_if_sentinel(v) for k, v in record.items()}


def load_records(path: str) -> list[dict[str, Any]]:
    """Parse a YAML, JSON, or CSV file and return a list of dicts.

    CSV values are always strings — type coercion happens in update_models.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = p.suffix.lower()

    if suffix in (".yml", ".yaml"):
        return _load_yaml(p)
    if suffix == ".json":
        return _load_json(p)
    if suffix == ".csv":
        return _load_csv(p)

    raise ValueError(
        f"Unsupported file format '{suffix}'. Supported formats: .yml, .yaml, .json, .csv"
    )


def _load_yaml(p: Path) -> list[dict[str, Any]]:
    import yaml  # lazy import — yaml is a dep but keep top-level imports minimal

    text = p.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(
            f"{p.name} must contain a list of records, got {type(data).__name__}"
        )
    return [_normalize_record(r) for r in data]


def _load_json(p: Path) -> list[dict[str, Any]]:
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(
            f"{p.name} must contain a JSON array, got {type(data).__name__}"
        )
    return [_normalize_record(r) for r in data]


def _load_csv(p: Path) -> list[dict[str, Any]]:
    with p.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [
            {k: _null_if_sentinel(v) for k, v in row.items() if v != ""}
            for row in reader
        ]
