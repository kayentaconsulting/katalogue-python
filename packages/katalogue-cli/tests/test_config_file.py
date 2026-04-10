"""Unit tests for load_config_file."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from katalogue_cli.config.file import clear_client_id, load_config_file


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def config_file(config_dir: Path) -> Path:
    return config_dir / "config.toml"


class TestMissingFile:
    def test_returns_empty_dict_when_no_file(self, config_dir: Path) -> None:
        assert load_config_file(config_dir=config_dir) == {}

    def test_no_warning_when_file_absent(
        self, config_dir: Path, capsys: pytest.CaptureFixture
    ) -> None:
        load_config_file(config_dir=config_dir)
        assert capsys.readouterr().err == ""


class TestValidFile:
    def test_returns_client_id(self, config_dir: Path, config_file: Path) -> None:
        config_file.write_text('client_id = "from-file"\n', encoding="utf-8")
        assert load_config_file(config_dir=config_dir) == {"client_id": "from-file"}

    def test_returns_base_url(self, config_dir: Path, config_file: Path) -> None:
        config_file.write_text(
            'base_url = "https://custom.example.com"\n', encoding="utf-8"
        )
        assert load_config_file(config_dir=config_dir) == {
            "base_url": "https://custom.example.com"
        }

    def test_returns_token_url(self, config_dir: Path, config_file: Path) -> None:
        config_file.write_text(
            'token_url = "https://custom.example.com/oidc/token"\n', encoding="utf-8"
        )
        assert load_config_file(config_dir=config_dir) == {
            "token_url": "https://custom.example.com/oidc/token"
        }

    def test_returns_all_allowed_keys(
        self, config_dir: Path, config_file: Path
    ) -> None:
        config_file.write_text(
            'client_id = "my-id"\n'
            'base_url = "https://custom.example.com"\n'
            'token_url = "https://custom.example.com/oidc/token"\n',
            encoding="utf-8",
        )
        result = load_config_file(config_dir=config_dir)
        assert result == {
            "client_id": "my-id",
            "base_url": "https://custom.example.com",
            "token_url": "https://custom.example.com/oidc/token",
        }

    def test_ignores_client_secret(self, config_dir: Path, config_file: Path) -> None:
        config_file.write_text(
            'client_id = "my-id"\nclient_secret = "oops"\n', encoding="utf-8"
        )
        result = load_config_file(config_dir=config_dir)
        assert "client_secret" not in result
        assert result.get("client_id") == "my-id"

    def test_ignores_unknown_keys(self, config_dir: Path, config_file: Path) -> None:
        config_file.write_text('foobar = "baz"\nclient_id = "ok"\n', encoding="utf-8")
        result = load_config_file(config_dir=config_dir)
        assert "foobar" not in result

    def test_partial_keys_only_returns_present(
        self, config_dir: Path, config_file: Path
    ) -> None:
        config_file.write_text(
            'base_url = "https://custom.example.com"\n', encoding="utf-8"
        )
        result = load_config_file(config_dir=config_dir)
        assert list(result.keys()) == ["base_url"]


class TestBadToml:
    def test_bad_toml_returns_empty_dict(
        self, config_dir: Path, config_file: Path
    ) -> None:
        config_file.write_text("[[[not toml", encoding="utf-8")
        assert load_config_file(config_dir=config_dir) == {}

    def test_bad_toml_warns_to_stderr(
        self, config_dir: Path, config_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config_file.write_text("[[[not toml", encoding="utf-8")
        load_config_file(config_dir=config_dir)
        assert capsys.readouterr().err != ""

    def test_bad_toml_warning_includes_filename(
        self, config_dir: Path, config_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config_file.write_text("[[[not toml", encoding="utf-8")
        load_config_file(config_dir=config_dir)
        assert str(config_file) in capsys.readouterr().err


@pytest.mark.skipif(os.name == "nt", reason="Unix permissions only")
class TestPermissions:
    def test_world_readable_warns_to_stderr(
        self, config_dir: Path, config_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config_file.write_text('client_id = "ok"\n', encoding="utf-8")
        config_file.chmod(0o644)
        load_config_file(config_dir=config_dir)
        assert capsys.readouterr().err != ""

    def test_world_readable_still_returns_data(
        self, config_dir: Path, config_file: Path
    ) -> None:
        config_file.write_text('client_id = "ok"\n', encoding="utf-8")
        config_file.chmod(0o644)
        assert load_config_file(config_dir=config_dir).get("client_id") == "ok"

    def test_world_readable_warning_mentions_file_path(
        self, config_dir: Path, config_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config_file.write_text('client_id = "ok"\n', encoding="utf-8")
        config_file.chmod(0o644)
        load_config_file(config_dir=config_dir)
        assert str(config_file) in capsys.readouterr().err

    def test_correct_permissions_no_warning(
        self, config_dir: Path, config_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config_file.write_text('client_id = "ok"\n', encoding="utf-8")
        config_file.chmod(0o600)
        load_config_file(config_dir=config_dir)
        assert capsys.readouterr().err == ""

    def test_group_readable_also_warns(
        self, config_dir: Path, config_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config_file.write_text('client_id = "ok"\n', encoding="utf-8")
        config_file.chmod(0o640)
        load_config_file(config_dir=config_dir)
        assert capsys.readouterr().err != ""


class TestClearClientId:
    def test_removes_client_id_keeps_urls(
        self, config_dir: Path, config_file: Path
    ) -> None:
        config_file.write_text(
            'client_id = "cid"\nbase_url = "https://x.example.com"\ntoken_url = "https://x.example.com/oidc/token"\n'
        )
        clear_client_id(config_dir=config_dir)
        result = load_config_file(config_dir=config_dir)
        assert "client_id" not in result
        assert result["base_url"] == "https://x.example.com"
        assert result["token_url"] == "https://x.example.com/oidc/token"

    def test_deletes_file_when_only_client_id_remains(
        self, config_dir: Path, config_file: Path
    ) -> None:
        config_file.write_text('client_id = "cid"\n')
        clear_client_id(config_dir=config_dir)
        assert not config_file.exists()

    def test_no_op_when_file_absent(self, config_dir: Path) -> None:
        clear_client_id(config_dir=config_dir)  # must not raise

    def test_no_op_when_client_id_not_in_file(
        self, config_dir: Path, config_file: Path
    ) -> None:
        config_file.write_text('base_url = "https://x.example.com"\n')
        clear_client_id(config_dir=config_dir)
        result = load_config_file(config_dir=config_dir)
        assert result["base_url"] == "https://x.example.com"


class TestConfigDirDefault:
    def test_config_dir_none_does_not_raise(self) -> None:
        result = load_config_file(config_dir=None)
        assert result == {} or isinstance(result, dict)
