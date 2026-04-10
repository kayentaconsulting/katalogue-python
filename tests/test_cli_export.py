"""Tests for CLI export commands."""

import json

from katalogue.cli.main import cli
from katalogue.client.api import AuthError, ApiError

SYSTEM_EXPORT = {
    "meta": {
        "katalogue_env": "PROD",
        "katalogue_version": "1.0.0",
        "created_timestamp": "2026-01-01T00:00:00Z",
    },
    "data": {
        "system": {"system_id": "abc", "system_name": "Finance", "datasources": []}
    },
}
GLOSSARY_EXPORT = {
    "meta": {
        "katalogue_env": "PROD",
        "katalogue_version": "1.0.0",
        "created_timestamp": "2026-01-01T00:00:00Z",
    },
    "data": [
        {
            "glossary_name": "Business Terms",
            "name": "Revenue",
            "description": "Total income",
            "is_pii": False,
        }
    ],
}


class TestExportSystem:
    def test_happy_path_json(self, runner, cli_auth, mock_client):
        mock_client.get_system_export.return_value = SYSTEM_EXPORT
        result = runner.invoke(
            cli, [*cli_auth, "export", "system", "abc", "--format", "json"]
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["data"]["system"]["system_name"] == "Finance"
        assert parsed["meta"]["katalogue_env"] == "PROD"

    def test_happy_path_table(self, runner, cli_auth, mock_client):
        mock_client.get_system_export.return_value = SYSTEM_EXPORT
        result = runner.invoke(
            cli, [*cli_auth, "export", "system", "abc", "--format", "table"]
        )
        assert result.exit_code == 0
        assert "Finance" in result.output

    def test_calls_client_with_correct_id(self, runner, cli_auth, mock_client):
        mock_client.get_system_export.return_value = SYSTEM_EXPORT
        runner.invoke(cli, [*cli_auth, "export", "system", "abc"])
        mock_client.get_system_export.assert_called_once_with("abc")

    def test_auth_error(self, runner, cli_auth, mock_client):
        mock_client.get_system_export.side_effect = AuthError("Unauthorized")
        result = runner.invoke(cli, [*cli_auth, "export", "system", "abc"])
        assert result.exit_code == 1
        assert "Authentication failed" in result.output

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get_system_export.side_effect = ApiError("Not found")
        result = runner.invoke(cli, [*cli_auth, "export", "system", "abc"])
        assert result.exit_code == 1
        assert "Not found" in result.output


class TestExportGlossary:
    def test_happy_path_json(self, runner, cli_auth, mock_client):
        mock_client.get_glossary_export.return_value = GLOSSARY_EXPORT
        result = runner.invoke(
            cli, [*cli_auth, "export", "glossary", "42", "--format", "json"]
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["data"][0]["name"] == "Revenue"
        assert parsed["meta"]["katalogue_version"] == "1.0.0"

    def test_happy_path_table(self, runner, cli_auth, mock_client):
        mock_client.get_glossary_export.return_value = GLOSSARY_EXPORT
        result = runner.invoke(
            cli, [*cli_auth, "export", "glossary", "42", "--format", "table"]
        )
        assert result.exit_code == 0
        assert "Revenue" in result.output

    def test_calls_client_with_correct_id(self, runner, cli_auth, mock_client):
        mock_client.get_glossary_export.return_value = GLOSSARY_EXPORT
        runner.invoke(cli, [*cli_auth, "export", "glossary", "42"])
        mock_client.get_glossary_export.assert_called_once_with("42")

    def test_auth_error(self, runner, cli_auth, mock_client):
        mock_client.get_glossary_export.side_effect = AuthError("Unauthorized")
        result = runner.invoke(cli, [*cli_auth, "export", "glossary", "42"])
        assert result.exit_code == 1
        assert "Authentication failed" in result.output

    def test_api_error(self, runner, cli_auth, mock_client):
        mock_client.get_glossary_export.side_effect = ApiError("Glossary not found")
        result = runner.invoke(cli, [*cli_auth, "export", "glossary", "42"])
        assert result.exit_code == 1
        assert "Glossary not found" in result.output
