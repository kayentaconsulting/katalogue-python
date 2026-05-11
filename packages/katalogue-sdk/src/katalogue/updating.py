"""Update operations — fetch current record, merge user changes, PUT."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from katalogue.client.api import ApiError, AuthError
from katalogue.formatters import _draftjs_to_text
from katalogue.results import WriteResult
from katalogue.update_models import (
    BusinessTermUpdate,
    FieldDescriptionUpdate,
    GlossaryUpdate,
    validate_records,
)

if TYPE_CHECKING:
    from katalogue.client.api import KatalogueClient


def _unwrap(response: Any, resource: str, plural: str | None = None) -> Any:
    """Unwrap API envelope: {"business_term": {...}} or {"business_terms": [{...}]}."""
    if isinstance(response, dict):
        for key in filter(None, (plural, resource, f"{resource}s")):
            if key in response:
                inner = response[key]
                return inner[0] if isinstance(inner, list) and inner else inner
    return response


def _dump_changes(v: BaseModel) -> dict[str, Any]:
    """Dump validated record to a changes dict, preserving explicitly-set None values."""
    changes = v.model_dump(exclude_none=True)
    for field in v.model_fields_set:
        if getattr(v, field) is None:
            changes[field] = None
    return changes


def _prepare(
    client: "KatalogueClient",
    resource: str,
    model: type[BaseModel],
    id_field: str,
    record_id: int | str,
    changes: dict[str, Any],
    record_key: str | None = None,
) -> dict[str, Any]:
    """GET current record, filter to model fields, convert Draft.js, merge changes."""
    current = _unwrap(
        client.get_resource(resource, record_id), resource, plural=record_key
    )
    current = {
        k: (_draftjs_to_text(val) if isinstance(val, str) else val)
        for k, val in current.items()
        if k in model.model_fields and val is not None
    }
    return {**current, **changes}


def _fetch_and_put(
    client: "KatalogueClient",
    resource: str,
    model: type[BaseModel],
    id_field: str,
    record_key: str,
    scope_write: str,
    updates: list[dict[str, Any]],
    continue_on_error: bool = False,
) -> WriteResult:
    """GET each record, merge user changes on top, PUT.

    continue_on_error=False (default): batch all records in one PUT.
    continue_on_error=True: one PUT per record; failures are collected rather
    than raised so the remaining records are still attempted.
    """
    validated = validate_records(model, updates)

    if continue_on_error:
        partials: list[WriteResult] = []
        for v in validated:
            changes = _dump_changes(v)
            record_id = changes[id_field]
            try:
                merged = _prepare(
                    client,
                    resource,
                    model,
                    id_field,
                    record_id,
                    changes,
                    record_key=record_key,
                )
                raw = client._put_resource(
                    resource, scope_write, {record_key: [merged]}
                )
                partials.append(
                    WriteResult(
                        ok=raw.get("ok", True),
                        message=raw.get("message", ""),
                        data=raw.get(record_key, []),
                        record_id=record_id,
                    )
                )
            except (ApiError, AuthError) as e:
                partials.append(
                    WriteResult(ok=False, message=str(e), record_id=record_id)
                )

        combined_data = [item for r in partials if r.ok for item in r.data]
        return WriteResult(
            ok=all(r.ok for r in partials),
            message="",
            data=combined_data,
            partial_results=partials,
        )

    merged = []
    for v in validated:
        changes = v.model_dump(exclude_none=True)
        for field in v.model_fields_set:
            if getattr(v, field) is None:
                changes[field] = None
        record_id = changes[id_field]
        merged.append(
            _prepare(
                client,
                resource,
                model,
                id_field,
                record_id,
                changes,
                record_key=record_key,
            )
        )

    raw = client._put_resource(resource, scope_write, {record_key: merged})
    return WriteResult(
        ok=raw.get("ok", True),
        message=raw.get("message", ""),
        data=raw.get(record_key, []),
        raw=raw,
    )


def update_business_term(
    client: "KatalogueClient",
    updates: list[dict[str, Any]],
    continue_on_error: bool = False,
) -> WriteResult:
    return _fetch_and_put(
        client,
        "business_term",
        BusinessTermUpdate,
        "business_term_id",
        "business_terms",
        "business_term.write",
        updates,
        continue_on_error=continue_on_error,
    )


def update_field_description(
    client: "KatalogueClient",
    updates: list[dict[str, Any]],
    continue_on_error: bool = False,
) -> WriteResult:
    return _fetch_and_put(
        client,
        "field_description",
        FieldDescriptionUpdate,
        "field_description_id",
        "field_descriptions",
        "field_description.write",
        updates,
        continue_on_error=continue_on_error,
    )


def update_glossary(
    client: "KatalogueClient",
    updates: list[dict[str, Any]],
    continue_on_error: bool = False,
) -> WriteResult:
    return _fetch_and_put(
        client,
        "glossary",
        GlossaryUpdate,
        "glossary_id",
        "glossaries",
        "glossary.write",
        updates,
        continue_on_error=continue_on_error,
    )
