"""Serialization formatters for Katalogue API result sets."""

from __future__ import annotations

import json
from typing import Any


def format_json(data: Any) -> str:
    """Serialize data to a pretty-printed JSON string.

    format_json([{"id": 1, "name": "CDP"}])
    -> '[\\n  {\\n    "id": 1,\\n    "name": "CDP"\\n  }\\n]'
    """
    return json.dumps(data, indent=2, default=str)


def format_compact_json(data: Any) -> str:
    """Serialize data to a compact JSON string with no whitespace.

    format_compact_json([{"id": 1, "name": "CDP"}])
    -> '[{"id":1,"name":"CDP"}]'
    """
    return json.dumps(data, separators=(",", ":"), default=str)


def format_descriptions_to_plaintext(data: Any) -> Any:
    """Convert Draft.js rich-text JSON strings to plain text throughout a result set.

    Katalogue description fields may contain Draft.js JSON (a legacy rich-text
    format). This function extracts the readable text from those fields so
    callers receive clean strings without needing to parse the format themselves.
    Applied recursively — works on a single value, a dict, or a list of dicts.

    # single Draft.js string
    format_descriptions_to_plaintext('{"blocks":[{"text":"Hello world"}],"entityMap":{}}')
    -> "Hello world"

    # plain string — returned unchanged
    format_descriptions_to_plaintext("just text")
    -> "just text"

    # list of dicts — applied to all string values
    format_descriptions_to_plaintext([{"name": "A", "description": "<draftjs json>"}])
    -> [{"name": "A", "description": "extracted text"}]
    """
    if isinstance(data, str):
        return _draftjs_to_text(data)
    if isinstance(data, list):
        return [format_descriptions_to_plaintext(item) for item in data]
    if isinstance(data, dict):
        return {k: format_descriptions_to_plaintext(v) for k, v in data.items()}
    return data


def _draftjs_to_text(value: str) -> str:
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        return value
    if not isinstance(parsed, dict) or "blocks" not in parsed:
        return value
    return " ".join(b.get("text", "") for b in parsed["blocks"] if b.get("text"))


def format_resultset(data: Any, fmt: str | None) -> Any:
    """Serialize a result set to the requested format, or return the Python object.

    fmt="json"    -> pretty-printed JSON string
    fmt="compact" -> compact JSON string, no whitespace
    fmt=None      -> data returned as-is (Python dict or list)

    format_resultset([{"id": 1}], "json")    -> '[\\n  {"id": 1}\\n]'
    format_resultset([{"id": 1}], "compact") -> '[{"id":1}]'
    format_resultset([{"id": 1}], None)      -> [{"id": 1}]
    """
    if fmt == "json":
        return format_json(data)
    if fmt == "compact":
        return format_compact_json(data)
    return data
