"""Type mapping registry — resolve built-in, repo-registered, and file-path mappings."""

from __future__ import annotations

import importlib.resources
import tomllib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

from katalogue.datatype_converter import DatatypeConverterConfig

BUILTIN_DATATYPE_CONVERTERS: dict[str, str] = {
    "sqlserver-to-databricks": "sqlserver_to_databricks.yaml",
    "sqlserver-to-pyspark": "sqlserver_to_pyspark.yaml",
    "db2-to-databricks": "db2_to_databricks.yaml",
    "db2-to-pyspark": "db2_to_pyspark.yaml",
    "postgres-to-databricks": "postgres_to_databricks.yaml",
    "postgres-to-pyspark": "postgres_to_pyspark.yaml",
}


class DatatypeConverterDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Type mapping path cannot be empty")
        return value


def load_datatype_converter(
    name_or_path: str, start_dir: Path | None = None
) -> DatatypeConverterConfig:
    """Resolve and load a type mapping by name or file path.

    Resolution order:
    1. Repo-registered name (katalogue.toml / [tool.katalogue] in pyproject.toml)
    2. Built-in name
    3. Direct .yaml / .yml file path
    """
    # 1. Repo registry
    registry = _load_registry(start_dir=start_dir)
    if registry is not None:
        config_path, definitions = registry
        entry = definitions.get(name_or_path)
        if entry is not None:
            mapping_path = _resolve_path(entry.path, config_path.parent)
            return _parse_yaml(mapping_path)

    # 2. Built-in
    if name_or_path in BUILTIN_DATATYPE_CONVERTERS:
        package = importlib.resources.files("katalogue.datatype_converters")
        text = (package / BUILTIN_DATATYPE_CONVERTERS[name_or_path]).read_text(
            encoding="utf-8"
        )
        return _parse_text(text)

    # 3. Direct file path
    if _looks_like_path(name_or_path):
        path = Path(name_or_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Type mapping file not found: {path}")
        return _parse_yaml(path)

    builtins = ", ".join(sorted(BUILTIN_DATATYPE_CONVERTERS))
    raise ValueError(
        f"Unknown type mapping '{name_or_path}'. "
        f"Built-in mappings: {builtins}. "
        "Register a repo mapping in katalogue.toml, or provide a path to a .yaml file."
    )


def _looks_like_path(value: str) -> bool:
    p = Path(value)
    return p.suffix in {".yaml", ".yml"} or "/" in value or "\\" in value


def _resolve_path(path_value: str, config_dir: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = config_dir / path
    return path


def _parse_yaml(path: Path) -> DatatypeConverterConfig:
    text = path.read_text(encoding="utf-8")
    return _parse_text(text)


def _parse_text(text: str) -> DatatypeConverterConfig:
    data = yaml.safe_load(text) or {}
    return DatatypeConverterConfig(
        source=data.get("source", ""),
        target=data.get("target", ""),
        mappings=data.get("mappings", {}),
    )


# ---------------------------------------------------------------------------
# Registry discovery (same walk-up-to-git-root pattern as template_registry)
# ---------------------------------------------------------------------------


def _load_registry(
    start_dir: Path | None,
) -> tuple[Path, dict[str, DatatypeConverterDefinition]] | None:
    for directory in _iter_search_directories(start_dir):
        result = _load_registry_from_directory(directory)
        if result is not None:
            return result
    return None


def _iter_search_directories(start_dir: Path | None) -> list[Path]:
    start = Path.cwd() if start_dir is None else Path(start_dir)
    current = start if start.is_dir() else start.parent
    current = current.resolve()
    directories: list[Path] = []
    while True:
        directories.append(current)
        if current.parent == current or (current / ".git").exists():
            break
        current = current.parent
    return directories


def _load_registry_from_directory(
    directory: Path,
) -> tuple[Path, dict[str, DatatypeConverterDefinition]] | None:
    for filename, is_pyproject in [("katalogue.toml", False), ("pyproject.toml", True)]:
        config_file = directory / filename
        if config_file.is_file():
            result = _load_from_file(config_file, is_pyproject=is_pyproject)
            if result is not None:
                return config_file, result
    return None


def _load_from_file(
    path: Path, *, is_pyproject: bool
) -> dict[str, DatatypeConverterDefinition] | None:
    try:
        data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Could not parse config {path}: {exc}") from None

    if is_pyproject:
        raw = data.get("tool", {}).get("katalogue", {}).get("datatype_converters")
    else:
        raw = data.get("datatype_converters")

    if not isinstance(raw, dict) or not raw:
        return None

    return {name: DatatypeConverterDefinition(**defn) for name, defn in raw.items()}
