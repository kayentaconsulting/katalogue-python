"""Tests for client/api - OAuth2 HTTP client for Katalogue API."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from requests.exceptions import HTTPError

from katalogue.client.api import KatalogueClient, AuthError, ApiError
from katalogue.config.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def system_export_response():
    return json.loads((FIXTURES / "system_export.json").read_text())


@pytest.fixture
def error_401_response():
    return json.loads((FIXTURES / "error_401.json").read_text())


@pytest.fixture
def error_400_response():
    return json.loads((FIXTURES / "error_400.json").read_text())


def _make_response(status_code: int, json_data=None):
    """Create a mock response object with raise_for_status behaviour."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = HTTPError(response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


def _make_token_response():
    """Mock token response for OAuth2 token fetch."""
    return {
        "access_token": "mock-token",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


@pytest.fixture
def client():
    """Create a KatalogueClient with mocked OAuth2 token fetch."""
    with patch("katalogue.client.api.OAuth2Session") as MockSession:
        mock_session = MockSession.return_value
        mock_session.authorized = True  # Skip token fetch in tests
        settings = Settings(
            client_id="test-id",
            client_secret="test-secret",
            base_url="https://api.example.com",
            token_url="https://api.example.com/oauth/token",
        )
        c = KatalogueClient(settings)
        # Pre-set current scope so _ensure_token doesn't re-fetch
        c._current_scope = "system.read"
    return c


class TestGetSystemExport:
    def test_success_returns_parsed_dict(self, client, system_export_response):
        client._session.request.return_value = _make_response(200, system_export_response)
        result = client.get_system_export("abc123")
        assert result == system_export_response
        assert "meta" in result
        assert "data" in result

    def test_401_raises_auth_error(self, client, error_401_response):
        # First call returns 401, retry after refresh also 401
        client._session.request.return_value = _make_response(401, error_401_response)
        with pytest.raises(AuthError, match="[Uu]nauthorized|[Tt]oken"):
            client.get_system_export("abc123")

    def test_400_raises_api_error(self, client, error_400_response):
        client._session.request.return_value = _make_response(400, error_400_response)
        with pytest.raises(ApiError, match="Invalid system ID"):
            client.get_system_export("abc123")

    def test_500_raises_api_error(self, client):
        client._session.request.return_value = _make_response(500, {"error": "Internal server error"})
        with pytest.raises(ApiError):
            client.get_system_export("abc123")

    def test_request_url_is_correct(self, client, system_export_response):
        client._session.request.return_value = _make_response(200, system_export_response)
        client.get_system_export("abc123")
        client._session.request.assert_called_with("GET", "https://api.example.com/api/export/system/abc123")


class TestListResource:
    def test_returns_parsed_list(self, client):
        data = [{"id": "sys-001", "name": "CDP"}, {"id": "sys-002", "name": "PC"}]
        client._session.request.return_value = _make_response(200, data)
        result = client.list_resource("system")
        assert result == data
        assert len(result) == 2

    def test_401_raises_auth_error(self, client, error_401_response):
        client._session.request.return_value = _make_response(401, error_401_response)
        with pytest.raises(AuthError):
            client.list_resource("system")

    def test_empty_list(self, client):
        client._session.request.return_value = _make_response(200, [])
        result = client.list_resource("system")
        assert result == []

    def test_request_url_is_correct(self, client):
        client._session.request.return_value = _make_response(200, [])
        client.list_resource("system")
        client._session.request.assert_called_with("GET", "https://api.example.com/api/system/all")


class TestUrlEncoding:
    def test_resource_id_with_slash_is_encoded(self, client):
        client._session.request.return_value = _make_response(200, {"id": "1"})
        client.get_resource("system", "abc/def")
        client._session.request.assert_called_with("GET", "https://api.example.com/api/system/abc%2Fdef")

    def test_resource_id_with_dotdot_is_encoded(self, client):
        client._session.request.return_value = _make_response(200, {"id": "1"})
        client.get_resource("system", "../../etc")
        client._session.request.assert_called_with("GET", "https://api.example.com/api/system/..%2F..%2Fetc")

    def test_parent_id_with_slash_is_encoded(self, client):
        client._session.request.return_value = _make_response(200, [])
        client.list_by_parent("datasource", "system", "abc/def")
        client._session.request.assert_called_with("GET", "https://api.example.com/api/datasource/system/abc%2Fdef")

    def test_normal_id_is_unchanged(self, client):
        client._session.request.return_value = _make_response(200, {"id": "1"})
        client.get_resource("system", "abc-123")
        client._session.request.assert_called_with("GET", "https://api.example.com/api/system/abc-123")


class TestListByParent:
    def test_returns_parsed_list(self, client):
        data = [{"datasource_id": 1, "datasource_name": "katalogue"}]
        client._session.request.return_value = _make_response(200, data)
        result = client.list_by_parent("datasource", "system", "1")
        assert result == data

    def test_request_url_is_correct(self, client):
        client._session.request.return_value = _make_response(200, [])
        client.list_by_parent("datasource", "system", "1")
        client._session.request.assert_called_with("GET", "https://api.example.com/api/datasource/system/1")

    def test_uses_child_resource_scope(self, client):
        client._current_scope = None
        client._session.authorized = False
        client._session.request.return_value = _make_response(200, [])
        client.list_by_parent("datasource", "system", "1")
        call_kwargs = client._session.fetch_token.call_args
        assert call_kwargs[1]["scope"] == "datasource.read"


class TestTokenRefreshOn401:
    def test_retries_after_token_refresh(self, client, system_export_response):
        """First request returns 401, token is refreshed, retry succeeds."""
        client._session.request.side_effect = [
            _make_response(401, {"error": "token expired"}),
            _make_response(200, system_export_response),
        ]
        result = client.get_system_export("abc123")
        assert result == system_export_response
        assert client._session.fetch_token.called


class TestScopeDerivation:
    def test_list_resource_uses_resource_read_scope(self, client):
        """list_resource("system") should request scope "system.read"."""
        client._current_scope = None
        client._session.authorized = False
        client._session.request.return_value = _make_response(200, [])
        client.list_resource("system")
        client._session.fetch_token.assert_called_once()
        call_kwargs = client._session.fetch_token.call_args
        assert call_kwargs[1]["scope"] == "system.read"

    def test_get_resource_uses_resource_read_scope(self, client):
        client._current_scope = None
        client._session.authorized = False
        client._session.request.return_value = _make_response(200, {"id": "1"})
        client.get_resource("datasource", "ds-001")
        call_kwargs = client._session.fetch_token.call_args
        assert call_kwargs[1]["scope"] == "datasource.read"

    def test_scope_change_triggers_new_token(self, client):
        """Switching from system.read to datasource.read should re-fetch token."""
        client._current_scope = "system.read"
        client._session.authorized = True
        client._session.request.return_value = _make_response(200, [])
        client.list_resource("datasource")
        client._session.fetch_token.assert_called_once()
        call_kwargs = client._session.fetch_token.call_args
        assert call_kwargs[1]["scope"] == "datasource.read"
