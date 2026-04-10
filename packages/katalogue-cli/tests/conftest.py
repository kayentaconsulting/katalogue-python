"""Shared test fixtures for katalogue-cli."""

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def cli_auth():
    """Standard CLI auth args for tests that need a valid client."""
    return ["--client-id", "test-id", "--client-secret", "test-secret"]


@pytest.fixture
def mock_client(mocker):
    """Patched KatalogueClient. Returns the mock instance directly.

    Usage:
        def test_something(runner, cli_auth, mock_client):
            mock_client.get_resource.return_value = {"id": 1}
            result = runner.invoke(cli, [*cli_auth, "system", "get", "1"])
    """
    mock = mocker.patch("katalogue_cli.cli.common.KatalogueClient")
    return mock.return_value
