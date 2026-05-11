"""Tests for KatalogueClient.update() — public write entry point."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr
from requests.exceptions import HTTPError

from katalogue.client.api import ApiError, AuthError, KatalogueClient
from katalogue.config.settings import Settings
from katalogue.options import UpdateOptions
from katalogue.results import WriteResult


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
        object.__setattr__(c, "_session", mock_session)
        yield c


_FULL_TERM = {
    "business_term_id": 1,
    "business_term_name": "Revenue",
    "business_term_description": "Old",
    "status_id": 1,
    "owner_principal_id": 99,
    "glossary_id": 5,
}


class TestClientUpdate:
    def test_returns_write_result(self, client):
        client._session.request.side_effect = [
            _make_response(200, {"business_terms": [_FULL_TERM]}),
            _make_response(
                200, {"ok": True, "message": "updated", "business_terms": [_FULL_TERM]}
            ),
        ]
        opts = UpdateOptions(
            resource_id=1, changes={"business_term_description": "New"}
        )
        result = client.update("business_term", opts)
        assert isinstance(result, WriteResult)
        assert result.ok is True

    def test_invalid_resource_raises_value_error(self, client):
        opts = UpdateOptions(resource_id=1, changes={"system_name": "x"})
        with pytest.raises(ValueError, match="system"):
            client.update("system", opts)

    def test_propagates_auth_error(self, client):
        # GET succeeds; PUT returns 401 twice (initial + retry)
        client._session.request.side_effect = [
            _make_response(200, {"business_terms": [_FULL_TERM]}),
            _make_response(401, None),
            _make_response(401, None),
        ]
        opts = UpdateOptions(resource_id=1, changes={"business_term_description": "x"})
        with pytest.raises(AuthError):
            client.update("business_term", opts)

    def test_propagates_api_error_on_400(self, client):
        client._session.request.side_effect = [
            _make_response(200, {"business_terms": [_FULL_TERM]}),
            _make_response(400, {"detail": "validation failed"}),
        ]
        opts = UpdateOptions(resource_id=1, changes={"business_term_description": "x"})
        with pytest.raises(ApiError):
            client.update("business_term", opts)

    def test_batch_via_records(self, client):
        full_term_2 = {
            **_FULL_TERM,
            "business_term_id": 2,
            "business_term_name": "Cost",
        }
        client._session.request.side_effect = [
            _make_response(200, {"business_terms": [_FULL_TERM]}),
            _make_response(200, {"business_terms": [full_term_2]}),
            _make_response(200, {"ok": True, "message": "ok", "business_terms": []}),
        ]
        opts = UpdateOptions(
            records=[
                {"business_term_id": 1, "business_term_description": "A"},
                {"business_term_id": 2, "business_term_description": "B"},
            ]
        )
        result = client.update("business_term", opts)
        assert result.ok is True
        assert client._session.request.call_count == 3
