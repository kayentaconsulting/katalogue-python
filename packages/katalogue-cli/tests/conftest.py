"""Shared test fixtures for katalogue-cli."""

from typing import Any

import pytest
from click.testing import CliRunner

from katalogue import CatalogResult
from katalogue_cli.formatters.output import format_compact_json, format_json


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def cli_auth():
    """Standard CLI auth args for tests that need a valid client."""
    return [
        "--client-id",
        "test-id",
        "--client-secret",
        "test-secret",
        "--base-url",
        "https://test.katalogue.se",
    ]


@pytest.fixture
def mock_client(mocker):
    """Patched KatalogueClient. Returns the mock instance directly.

    Usage:
        def test_something(runner, cli_auth, mock_client):
            mock_client.get.return_value = CatalogResult(data={"id": 1}, output="...")
            result = runner.invoke(cli, [*cli_auth, "system", "get", "1"])
    """
    mock = mocker.patch("katalogue_cli.cli.common.KatalogueClient")
    mock.return_value.get.return_value = CatalogResult(data=[], output="[]")
    return mock.return_value


def _catalog_result(data: Any, fmt: str | None = None, **kwargs: Any) -> CatalogResult:
    output = kwargs.pop("output", None)
    if output is None and fmt == "json":
        output = format_json(data)
    elif output is None and fmt == "compact":
        output = format_compact_json(data)
    return CatalogResult(data=data, output=output, **kwargs)


@pytest.fixture
def catalog_result():
    """Factory for mocked SDK CatalogResult values."""
    return _catalog_result
