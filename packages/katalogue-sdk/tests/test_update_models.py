"""Tests for update_models — Pydantic input validation for sparse update records."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from katalogue.update_models import (
    BusinessTermUpdate,
    FieldDescriptionUpdate,
    GlossaryUpdate,
    validate_records,
)


class TestBusinessTermUpdate:
    def test_requires_id(self):
        with pytest.raises(ValidationError, match="business_term_id"):
            BusinessTermUpdate()  # type: ignore[call-arg]

    def test_all_content_fields_optional(self):
        m = BusinessTermUpdate(business_term_id=42)
        assert m.business_term_id == 42
        assert m.business_term_name is None
        assert m.business_term_description is None
        assert m.business_term_definition is None
        assert m.business_term_example is None

    def test_unknown_fields_ignored(self):
        m = BusinessTermUpdate(business_term_id=1, extra_col="ignored")  # type: ignore[call-arg]
        assert not hasattr(m, "extra_col")

    def test_string_id_coerced_to_int(self):
        m = BusinessTermUpdate(business_term_id="42")  # type: ignore[arg-type]
        assert m.business_term_id == 42

    def test_partial_fields_round_trip(self):
        m = BusinessTermUpdate(
            business_term_id=7,
            business_term_description="New desc",
        )
        d = m.model_dump(exclude_none=True)
        assert d == {"business_term_id": 7, "business_term_description": "New desc"}


class TestFieldDescriptionUpdate:
    def test_requires_id(self):
        with pytest.raises(ValidationError, match="field_description_id"):
            FieldDescriptionUpdate()  # type: ignore[call-arg]

    def test_is_pii_accepts_bool(self):
        m = FieldDescriptionUpdate(field_description_id=3, is_pii=True)
        assert m.is_pii is True

    def test_is_pii_string_coercion(self):
        # Pydantic coerces "true"/"false" strings to bool
        m = FieldDescriptionUpdate(field_description_id=3, is_pii="true")  # type: ignore[arg-type]
        assert m.is_pii is True

    def test_unknown_fields_ignored(self):
        m = FieldDescriptionUpdate(field_description_id=1, garbage="x")  # type: ignore[call-arg]
        assert not hasattr(m, "garbage")


class TestGlossaryUpdate:
    def test_requires_id(self):
        with pytest.raises(ValidationError, match="glossary_id"):
            GlossaryUpdate()  # type: ignore[call-arg]

    def test_optional_fields_default_none(self):
        m = GlossaryUpdate(glossary_id=5)
        assert m.glossary_name is None
        assert m.glossary_description is None


class TestTimestampFields:
    def test_timestamps_stripped_from_put_payload(self):
        allowed = set(BusinessTermUpdate.model_fields.keys())
        assert "created_timestamp" not in allowed
        assert "modified_timestamp" not in allowed

    def test_field_description_timestamps_stripped(self):
        allowed = set(FieldDescriptionUpdate.model_fields.keys())
        assert "created_timestamp" not in allowed
        assert "modified_timestamp" not in allowed

    def test_glossary_timestamps_stripped(self):
        allowed = set(GlossaryUpdate.model_fields.keys())
        assert "created_timestamp" not in allowed
        assert "modified_timestamp" not in allowed


class TestValidateRecords:
    def test_all_valid_returns_models(self):
        records = [
            {"business_term_id": 1, "business_term_description": "a"},
            {"business_term_id": 2, "business_term_name": "b"},
        ]
        result = validate_records(BusinessTermUpdate, records)
        assert len(result) == 2
        assert result[0].business_term_id == 1  # type: ignore[attr-defined]

    def test_collects_all_errors_not_just_first(self):
        records = [
            {"business_term_name": "missing id"},  # row 0 — missing id
            {"business_term_id": 2},  # row 1 — valid
            {"business_term_name": "also missing"},  # row 2 — missing id
        ]
        with pytest.raises(ValueError) as exc_info:
            validate_records(BusinessTermUpdate, records)
        msg = str(exc_info.value)
        assert "Row 0" in msg
        assert "Row 2" in msg
        assert "Row 1" not in msg  # valid row not mentioned

    def test_error_message_names_missing_field(self):
        with pytest.raises(ValueError, match="business_term_id"):
            validate_records(BusinessTermUpdate, [{"business_term_name": "x"}])

    def test_empty_list_returns_empty(self):
        assert validate_records(BusinessTermUpdate, []) == []
