"""Config file loader for katalogue-cli.

Reads non-secret settings from ~/.config/katalogue/config.toml (or OS equivalent).
client_secret is never stored here — use the OS keychain (Slice 3) or env vars.
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

import platformdirs

_CONFIG_FILENAME = "config.toml"
_ALLOWED_KEYS = {"client_id", "base_url", "token_url"}


def load_config_file(config_dir: Path | None = None) -> dict:
    """Load non-secret settings from the config file.

    Returns a dict containing only the subset of allowed keys that are present.
    Never returns client_secret. Returns {} on any error (missing, bad TOML).

    Args:
        config_dir: Override the config directory (for testing). Defaults to
            the OS user config dir via platformdirs.
    """
    if config_dir is not None:
        path = config_dir / _CONFIG_FILENAME
    else:
        path = Path(platformdirs.user_config_dir("katalogue")) / _CONFIG_FILENAME

    if not path.exists():
        return {}

    if os.name != "nt":
        mode = path.stat().st_mode & 0o777
        if mode & 0o077 != 0:
            print(
                f"Warning: {path} has insecure permissions ({oct(mode)}). "
                "Run: chmod 600 " + str(path),
                file=sys.stderr,
            )

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Warning: could not parse config file {path}: {exc}", file=sys.stderr)
        return {}

    return {k: v for k, v in data.items() if k in _ALLOWED_KEYS}


def write_config_file(
    client_id: str,
    base_url: str,
    token_url: str,
    config_dir: Path | None = None,
) -> None:
    """Write non-secret settings to the config file.

    Never writes client_secret. Creates parent directories as needed.
    Writes atomically (temp file + os.replace) with mode 0o600 on POSIX.

    Args:
        config_dir: Override the config directory (for testing).
    """
    if config_dir is not None:
        path = config_dir / _CONFIG_FILENAME
    else:
        path = Path(platformdirs.user_config_dir("katalogue")) / _CONFIG_FILENAME

    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"client_id = {_toml_str(client_id)}\n"
        f"base_url = {_toml_str(base_url)}\n"
        f"token_url = {_toml_str(token_url)}\n"
    )
    tmp_path = path.parent / ".config.tmp"
    try:
        tmp_path.write_text(content, encoding="utf-8")
        if os.name != "nt":
            os.chmod(tmp_path, 0o600)
        os.replace(str(tmp_path), str(path))
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def clear_client_id(config_dir: Path | None = None) -> None:
    """Remove client_id from the config file, keeping base_url and token_url.

    If the resulting file would be empty, it is deleted. No-ops if the file
    does not exist.

    Args:
        config_dir: Override the config directory (for testing).
    """
    cfg = load_config_file(config_dir=config_dir)
    cfg.pop("client_id", None)

    if config_dir is not None:
        path = config_dir / _CONFIG_FILENAME
    else:
        path = Path(platformdirs.user_config_dir("katalogue")) / _CONFIG_FILENAME

    if not path.exists():
        return

    if not cfg:
        path.unlink(missing_ok=True)
        return

    lines = [f"{k} = {_toml_str(v)}\n" for k, v in cfg.items() if isinstance(v, str)]
    content = "".join(lines)
    tmp_path = path.parent / ".config.tmp"
    try:
        tmp_path.write_text(content, encoding="utf-8")
        if os.name != "nt":
            os.chmod(tmp_path, 0o600)
        os.replace(str(tmp_path), str(path))
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _toml_str(value: str) -> str:
    """Format a Python string as a TOML string literal."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
