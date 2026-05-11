"""Pydantic validation models for sparse update input records."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError


class BusinessTermUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    business_term_id: int
    business_term_name: str | None = None
    business_term_description: str | None = None
    business_term_definition: str | None = None
    business_term_example: str | None = None
    business_term_type_id: int | None = None
    parent_business_term_id: int | None = None
    status_id: int | None = None
    owner_principal_id: int | None = None
    glossary_id: int | None = None


class FieldDescriptionUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    field_description_id: int
    field_description_name: str | None = None
    field_description_description: str | None = None
    field_description_definition: str | None = None
    field_description_example: str | None = None
    is_pii: bool | None = None
    field_role_id: int | None = None
    field_unit_id: int | None = None
    field_sensitivity_id: int | None = None
    status_id: int | None = None
    owner_principal_id: int | None = None


class GlossaryUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    glossary_id: int
    glossary_name: str | None = None
    glossary_description: str | None = None
    owner_principal_id: int | None = None
    status_id: int | None = None


def validate_records(
    model: type[BaseModel],
    records: list[dict[str, Any]],
) -> list[BaseModel]:
    """Validate all records against a model, collecting all errors before raising.

    Raises ValueError listing every invalid row if any fail validation.
    """
    results: list[BaseModel] = []
    errors: list[str] = []

    for i, record in enumerate(records):
        try:
            results.append(model(**record))
        except ValidationError as e:
            for err in e.errors():
                field = ".".join(str(loc) for loc in err["loc"])
                errors.append(f"  Row {i}: '{field}' — {err['msg']}")

    if errors:
        raise ValueError("Validation failed:\n" + "\n".join(errors))

    return results
