"""Tests for KatalogueClient.get_changelog()."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr
from requests.exceptions import HTTPError

from katalogue.client.api import ApiError, AuthError, KatalogueClient
from katalogue.config.settings import Settings

BASE = "https://api.example.com"


def _make_response(status_code: int, json_data=None) -> MagicMock:
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
        c = KatalogueClient(
            Settings(
                client_id="test-id",
                client_secret=SecretStr("test-secret"),
                base_url=BASE,
                token_url=f"{BASE}/oauth/token",
            )
        )
    return c


_ENTRY_RECENT = {
    "changelog_id": 1,
    "created_timestamp": "2024-06-01T12:00:00Z",
    "operation": "U",
    "object_name": "system",
    "object_id": 5,
    "changed_by_user_username": "alice",
    "changed_by_user_fullname": "Alice Smith",
    "old_data": None,
    "new_data": None,
}
_ENTRY_OLD = {
    "changelog_id": 2,
    "created_timestamp": "2023-11-01T08:00:00Z",
    "operation": "I",
    "object_name": "system",
    "object_id": 5,
    "changed_by_user_username": "bob",
    "changed_by_user_fullname": "Bob Jones",
    "old_data": None,
    "new_data": None,
}


class TestGetChangelogSingleAsset:
    def test_correct_url_called(self, client) -> None:
        client._session.request.return_value = _make_response(200, {"changelog": []})
        client.get_changelog("system", 5)
        client._session.request.assert_called_with(
            "GET", f"{BASE}/api/changelog/system/5"
        )

    def test_uses_changelog_read_scope(self, client) -> None:
        client._current_scope = None
        client._session.authorized = False
        client._session.request.return_value = _make_response(200, {"changelog": []})
        client.get_changelog("system", 5)
        assert client._session.fetch_token.call_args[1]["scope"] == "changelog.read"

    def test_returns_catalog_result_with_entries(self, client) -> None:
        client._session.request.return_value = _make_response(
            200, {"changelog": [_ENTRY_RECENT, _ENTRY_OLD]}
        )
        result = client.get_changelog("system", 5)
        assert len(result.data) == 2

    def test_empty_changelog_returns_empty_list(self, client) -> None:
        client._session.request.return_value = _make_response(200, {"changelog": []})
        result = client.get_changelog("system", 5)
        assert result.data == []

    def test_entries_sorted_by_timestamp_descending(
        self, client
    ) -> None:
        client._session.request.return_value = _make_response(
            200, {"changelog": [_ENTRY_OLD, _ENTRY_RECENT]}
        )
        result = client.get_changelog("system", 5)
        assert result.data[0]["changelog_id"] == 1  # newer first

    def test_metadata_strategy(self, client) -> None:
        client._session.request.return_value = _make_response(200, {"changelog": []})
        result = client.get_changelog("system", 5)
        assert result.metadata["strategy"] == "changelog_asset"

    def test_401_raises_auth_error(self, client) -> None:
        client._session.request.return_value = _make_response(
            401, {"message": "Unauthorized"}
        )
        with pytest.raises(AuthError):
            client.get_changelog("system", 5)

    def test_500_raises_api_error(self, client) -> None:
        client._session.request.return_value = _make_response(
            500, {"error": "Server error"}
        )
        with pytest.raises(ApiError):
            client.get_changelog("system", 5)

    def test_unknown_object_name_raises_value_error(
        self, client
    ) -> None:
        with pytest.raises(ValueError, match="Invalid object_name"):
            client.get_changelog("not_real", 5)


class TestGetChangelogJob:
    def test_correct_url_for_job(self, client) -> None:
        client._session.request.return_value = _make_response(200, {"changelog": []})
        client.get_changelog("job", 7)
        client._session.request.assert_called_with("GET", f"{BASE}/api/changelog/job/7")

    def test_job_metadata_strategy(self, client) -> None:
        client._session.request.return_value = _make_response(200, {"changelog": []})
        result = client.get_changelog("job", 7)
        assert result.metadata["strategy"] == "changelog_job"

    def test_job_returns_entries(self, client) -> None:
        entry = {**_ENTRY_RECENT, "job_id": 7}
        client._session.request.return_value = _make_response(
            200, {"changelog": [entry]}
        )
        result = client.get_changelog("job", 7)
        assert len(result.data) == 1


class TestGetChangelogDateFilter:
    def test_from_date_excludes_older_entries(self, client) -> None:
        client._session.request.return_value = _make_response(
            200, {"changelog": [_ENTRY_RECENT, _ENTRY_OLD]}
        )
        result = client.get_changelog("system", 5, from_date="2024-01-01")
        assert len(result.data) == 1
        assert result.data[0]["changelog_id"] == 1

    def test_to_date_excludes_newer_entries(self, client) -> None:
        client._session.request.return_value = _make_response(
            200, {"changelog": [_ENTRY_RECENT, _ENTRY_OLD]}
        )
        result = client.get_changelog("system", 5, to_date="2023-12-31")
        assert len(result.data) == 1
        assert result.data[0]["changelog_id"] == 2

    def test_from_and_to_combined(self, client) -> None:
        client._session.request.return_value = _make_response(
            200, {"changelog": [_ENTRY_RECENT, _ENTRY_OLD]}
        )
        result = client.get_changelog(
            "system", 5, from_date="2024-01-01", to_date="2024-12-31"
        )
        assert len(result.data) == 1
        assert result.data[0]["changelog_id"] == 1

    def test_no_date_filter_returns_all(self, client) -> None:
        client._session.request.return_value = _make_response(
            200, {"changelog": [_ENTRY_RECENT, _ENTRY_OLD]}
        )
        result = client.get_changelog("system", 5)
        assert len(result.data) == 2


class TestGetChangelogHierarchical:
    def test_include_children_fetches_system_and_datasources(
        self, client
    ) -> None:
        ds_entry = {**_ENTRY_RECENT, "object_name": "datasource", "changelog_id": 10}

        def _respond(method: str, url: str, **_) -> MagicMock:
            if url == f"{BASE}/api/changelog/system/5":
                return _make_response(200, {"changelog": [_ENTRY_RECENT]})
            if url == f"{BASE}/api/datasource/system/5":
                return _make_response(200, [{"datasource_id": 10, "system_id": 5}])
            if url == f"{BASE}/api/changelog/datasource/10":
                return _make_response(200, {"changelog": [ds_entry]})
            # no children below datasource 10
            return _make_response(200, [])

        client._session.request.side_effect = _respond
        result = client.get_changelog("system", 5, include_children=True)
        assert len(result.data) == 2
        assert result.metadata["strategy"] == "changelog_hierarchical"

    def test_include_children_stops_on_empty_level(
        self, client
    ) -> None:
        def _respond(method: str, url: str, **_) -> MagicMock:
            if url == f"{BASE}/api/changelog/system/5":
                return _make_response(200, {"changelog": [_ENTRY_RECENT]})
            if url == f"{BASE}/api/datasource/system/5":
                return _make_response(200, [])  # no datasources
            return _make_response(200, {"changelog": []})

        client._session.request.side_effect = _respond
        result = client.get_changelog("system", 5, include_children=True)
        assert len(result.data) == 1  # only the system's own entry
