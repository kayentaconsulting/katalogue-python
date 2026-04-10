"""Integration tests: verify common.py wires DiskTokenCache into KatalogueClient."""

from __future__ import annotations

from unittest.mock import MagicMock

from click.testing import CliRunner

from katalogue_cli.cli.main import cli
from katalogue_cli.auth import DiskTokenCache


def _auth_args() -> list[str]:
    return ["--client-id", "test-id", "--client-secret", "test-secret"]


def test_client_receives_disk_token_cache(runner: CliRunner, mocker) -> None:
    """KatalogueClient must be constructed with a DiskTokenCache instance."""
    mock_cls = mocker.patch("katalogue_cli.cli.common.KatalogueClient")
    mock_instance = MagicMock()
    mock_instance.list_resource.return_value = []
    mock_cls.return_value = mock_instance

    result = runner.invoke(cli, [*_auth_args(), "system", "list"])
    assert result.exit_code == 0

    call_kwargs = mock_cls.call_args.kwargs
    assert "token_cache" in call_kwargs
    assert isinstance(call_kwargs["token_cache"], DiskTokenCache)


def test_disk_cache_instantiated_once_per_invocation(runner: CliRunner, mocker) -> None:
    """DiskTokenCache is created once per CLI invocation, not per API call."""
    mock_cls = mocker.patch("katalogue_cli.cli.common.KatalogueClient")
    mock_instance = MagicMock()
    mock_instance.list_resource.return_value = []
    mock_cls.return_value = mock_instance

    init_count: list[int] = [0]
    original_init = DiskTokenCache.__init__

    def counting_init(self, **kwargs) -> None:
        init_count[0] += 1
        original_init(self, **kwargs)

    mocker.patch.object(DiskTokenCache, "__init__", counting_init)

    runner.invoke(cli, [*_auth_args(), "system", "list"])
    assert init_count[0] == 1
