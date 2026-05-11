"""Tests for updating.py — fetch-then-PUT with model-field passthrough."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr
from requests.exceptions import HTTPError

from katalogue.client.api import KatalogueClient
from katalogue.config.settings import Settings
from katalogue.results import WriteResult
from katalogue.updating import (
    update_business_term,
    update_field_description,
    update_glossary,
)


def _make_response(status_code: int, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = HTTPError(response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def client():
    with patch("katalogue.client.api.OAuth2Session") as MockSession:
        mock_session = MockSession.return_value
        mock_session.authorized = True
        mock_session.token = {
            "access_token": "mock-token",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }
        settings = Settings(
            client_id="test-id",
            client_secret=SecretStr("test-secret"),
            base_url="https://api.example.com",
            token_url="https://api.example.com/oauth/token",
        )
        c = KatalogueClient(settings=settings)
        c._session = mock_session
        yield c


_STORED_TERM = {
    "business_term_id": 42,
    "business_term_name": "Revenue",
    "business_term_description": "Old description",
    "business_term_definition": None,
    "business_term_example": None,
    "status_id": 1,
    "owner_principal_id": 99,
    "glossary_id": 5,
    "business_term_type_id": None,
    "parent_business_term_id": None,
    "created_timestamp": "2024-01-01",
    "modified_timestamp": "2024-06-01",
    "glossary_name": "Finance",
    "business_term_type_name": None,
    "business_term_type_description": None,
}


def _get(data):
    return _make_response(200, {"business_terms": [data]})


def _put_ok(record_key="business_terms"):
    return _make_response(200, {"ok": True, "message": "updated", record_key: []})


class TestUpdateBusinessTerm:
    def test_fetches_then_puts(self, client):
        client._session.request.side_effect = [_get(_STORED_TERM), _put_ok()]
        result = update_business_term(
            client, [{"business_term_id": 42, "business_term_example": "new"}]
        )
        assert isinstance(result, WriteResult)
        assert result.ok is True
        assert client._session.request.call_count == 2
        assert client._session.request.call_args_list[0].args[0] == "GET"
        assert client._session.request.call_args_list[1].args[0] == "PUT"

    def test_user_change_overrides_fetched_value(self, client):
        client._session.request.side_effect = [_get(_STORED_TERM), _put_ok()]
        update_business_term(
            client, [{"business_term_id": 42, "business_term_example": "new"}]
        )
        sent = client._session.request.call_args_list[1].kwargs["json"][
            "business_terms"
        ][0]
        assert sent["business_term_example"] == "new"

    def test_required_fields_filled_from_get(self, client):
        client._session.request.side_effect = [_get(_STORED_TERM), _put_ok()]
        update_business_term(
            client, [{"business_term_id": 42, "business_term_example": "new"}]
        )
        sent = client._session.request.call_args_list[1].kwargs["json"][
            "business_terms"
        ][0]
        assert sent["business_term_name"] == "Revenue"
        assert sent["glossary_id"] == 5
        assert sent["owner_principal_id"] == 99

    def test_computed_fields_stripped(self, client):
        client._session.request.side_effect = [_get(_STORED_TERM), _put_ok()]
        update_business_term(client, [{"business_term_id": 42}])
        sent = client._session.request.call_args_list[1].kwargs["json"][
            "business_terms"
        ][0]
        assert "created_timestamp" not in sent
        assert "modified_timestamp" not in sent
        assert "glossary_name" not in sent
        assert "business_term_type_name" not in sent
        assert "business_term_type_description" not in sent

    def test_draftjs_description_converted_to_plain_text(self, client):
        draftjs = '{"blocks":[{"key":"a","text":"Plain text from draft","type":"unstyled","depth":0,"inlineStyleRanges":[],"entityRanges":[],"data":{}}],"entityMap":{}}'
        stored = {**_STORED_TERM, "business_term_description": draftjs}
        client._session.request.side_effect = [_get(stored), _put_ok()]
        update_business_term(
            client, [{"business_term_id": 42, "business_term_example": "ex"}]
        )
        sent = client._session.request.call_args_list[1].kwargs["json"][
            "business_terms"
        ][0]
        assert sent["business_term_description"] == "Plain text from draft"

    def test_null_fields_not_sent(self, client):
        client._session.request.side_effect = [_get(_STORED_TERM), _put_ok()]
        update_business_term(client, [{"business_term_id": 42}])
        sent = client._session.request.call_args_list[1].kwargs["json"][
            "business_terms"
        ][0]
        assert "business_term_definition" not in sent
        assert "business_term_example" not in sent
        assert "business_term_type_id" not in sent
        assert "parent_business_term_id" not in sent

    def test_batch_two_gets_one_put(self, client):
        stored2 = {**_STORED_TERM, "business_term_id": 43, "business_term_name": "Cost"}
        client._session.request.side_effect = [
            _get(_STORED_TERM),
            _get(stored2),
            _put_ok(),
        ]
        result = update_business_term(
            client,
            [
                {"business_term_id": 42, "business_term_example": "a"},
                {"business_term_id": 43, "business_term_example": "b"},
            ],
        )
        assert result.ok is True
        assert client._session.request.call_count == 3
        sent = client._session.request.call_args_list[2].kwargs["json"][
            "business_terms"
        ]
        assert sent[0]["business_term_example"] == "a"
        assert sent[1]["business_term_example"] == "b"

    def test_extra_csv_columns_ignored(self, client):
        client._session.request.side_effect = [_get(_STORED_TERM), _put_ok()]
        update_business_term(
            client, [{"business_term_id": 42, "glossary_name": "ignored"}]
        )
        sent = client._session.request.call_args_list[1].kwargs["json"][
            "business_terms"
        ][0]
        assert "glossary_name" not in sent

    def test_string_id_coerced_to_int(self, client):
        client._session.request.side_effect = [_get(_STORED_TERM), _put_ok()]
        update_business_term(
            client, [{"business_term_id": "42", "business_term_name": "X"}]
        )
        get_url = client._session.request.call_args_list[0].args[1]
        assert get_url.endswith("/42")

    def test_invalid_record_raises_before_http(self, client):
        with pytest.raises(ValueError, match="business_term_id"):
            update_business_term(client, [{"business_term_name": "no id"}])
        client._session.request.assert_not_called()

    def test_explicit_none_sent_as_null_in_put(self, client):
        client._session.request.side_effect = [_get(_STORED_TERM), _put_ok()]
        update_business_term(
            client, [{"business_term_id": 42, "business_term_description": None}]
        )
        sent = client._session.request.call_args_list[1].kwargs["json"][
            "business_terms"
        ][0]
        assert "business_term_description" in sent
        assert sent["business_term_description"] is None

    def test_explicit_none_overrides_fetched_value(self, client):
        stored = {**_STORED_TERM, "business_term_description": "old value"}
        client._session.request.side_effect = [_get(stored), _put_ok()]
        update_business_term(
            client, [{"business_term_id": 42, "business_term_description": None}]
        )
        sent = client._session.request.call_args_list[1].kwargs["json"][
            "business_terms"
        ][0]
        assert sent["business_term_description"] is None

    def test_write_result_data_from_put_response(self, client):
        updated = {**_STORED_TERM, "business_term_example": "final"}
        client._session.request.side_effect = [
            _get(_STORED_TERM),
            _make_response(
                200,
                {"ok": True, "message": "1 term updated", "business_terms": [updated]},
            ),
        ]
        result = update_business_term(client, [{"business_term_id": 42}])
        assert result.data == [updated]
        assert result.message == "1 term updated"


class TestContinueOnError:
    def test_sends_one_put_per_record(self, client):
        stored2 = {**_STORED_TERM, "business_term_id": 43, "business_term_name": "Cost"}
        client._session.request.side_effect = [
            _get(_STORED_TERM),
            _put_ok(),
            _get(stored2),
            _put_ok(),
        ]
        update_business_term(
            client,
            [
                {"business_term_id": 42, "business_term_example": "a"},
                {"business_term_id": 43, "business_term_example": "b"},
            ],
            continue_on_error=True,
        )
        puts = [c for c in client._session.request.call_args_list if c.args[0] == "PUT"]
        assert len(puts) == 2

    def test_partial_results_populated(self, client):
        stored2 = {**_STORED_TERM, "business_term_id": 43, "business_term_name": "Cost"}
        client._session.request.side_effect = [
            _get(_STORED_TERM),
            _put_ok(),
            _get(stored2),
            _put_ok(),
        ]
        result = update_business_term(
            client,
            [
                {"business_term_id": 42, "business_term_example": "a"},
                {"business_term_id": 43, "business_term_example": "b"},
            ],
            continue_on_error=True,
        )
        assert result.partial_results is not None
        assert len(result.partial_results) == 2
        assert result.partial_results[0].record_id == 42
        assert result.partial_results[1].record_id == 43

    def test_all_succeed_result_ok_true(self, client):
        stored2 = {**_STORED_TERM, "business_term_id": 43}
        client._session.request.side_effect = [
            _get(_STORED_TERM),
            _put_ok(),
            _get(stored2),
            _put_ok(),
        ]
        result = update_business_term(
            client,
            [{"business_term_id": 42}, {"business_term_id": 43}],
            continue_on_error=True,
        )
        assert result.ok is True
        assert all(r.ok for r in result.partial_results)

    def test_one_fails_result_ok_false(self, client):
        stored2 = {**_STORED_TERM, "business_term_id": 43}
        client._session.request.side_effect = [
            _get(_STORED_TERM),
            _put_ok(),
            _get(stored2),
            _make_response(400, {"detail": "backend error"}),
        ]
        result = update_business_term(
            client,
            [{"business_term_id": 42}, {"business_term_id": 43}],
            continue_on_error=True,
        )
        assert result.ok is False
        assert result.partial_results[0].ok is True
        assert result.partial_results[1].ok is False
        assert result.partial_results[1].record_id == 43

    def test_false_still_batches(self, client):
        stored2 = {**_STORED_TERM, "business_term_id": 43}
        client._session.request.side_effect = [
            _get(_STORED_TERM),
            _get(stored2),
            _put_ok(),
        ]
        update_business_term(
            client,
            [{"business_term_id": 42}, {"business_term_id": 43}],
            continue_on_error=False,
        )
        puts = [c for c in client._session.request.call_args_list if c.args[0] == "PUT"]
        assert len(puts) == 1

    def test_no_partial_results_when_false(self, client):
        client._session.request.side_effect = [_get(_STORED_TERM), _put_ok()]
        result = update_business_term(
            client, [{"business_term_id": 42}], continue_on_error=False
        )
        assert result.partial_results is None


class TestUpdateFieldDescription:
    def test_fetches_then_puts(self, client):
        stored = {
            "field_description_id": 5,
            "field_description_name": "Amount",
            "field_description_description": "Some desc",
            "field_description_definition": None,
            "field_description_example": None,
            "is_pii": False,
            "field_role_id": None,
            "field_unit_id": None,
            "field_sensitivity_id": None,
            "status_id": 1,
            "owner_principal_id": 2,
        }
        client._session.request.side_effect = [
            _make_response(200, {"field_descriptions": [stored]}),
            _make_response(
                200, {"ok": True, "message": "ok", "field_descriptions": []}
            ),
        ]
        result = update_field_description(
            client, [{"field_description_id": 5, "field_description_example": "ex"}]
        )
        assert result.ok is True
        assert client._session.request.call_count == 2


class TestUpdateGlossary:
    def test_fetches_then_puts(self, client):
        stored = {
            "glossary_id": 3,
            "glossary_name": "Finance",
            "glossary_description": "Old",
            "owner_principal_id": 1,
            "status_id": 2,
        }
        client._session.request.side_effect = [
            _make_response(200, {"glossaries": [stored]}),
            _make_response(200, {"ok": True, "message": "ok", "glossaries": []}),
        ]
        result = update_glossary(
            client, [{"glossary_id": 3, "glossary_name": "Finance Updated"}]
        )
        assert result.ok is True
        assert client._session.request.call_count == 2
