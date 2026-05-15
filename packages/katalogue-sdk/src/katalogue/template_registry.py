"""Repo-local template registry discovery and resolution."""

from __future__ import annotations

import importlib.resources
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

BUILTIN_TEMPLATES: dict[str, str] = {
    "dbt-source": "dbt_source.j2",
    "column-mapping": "column_mapping.j2",
    "json-template": "json_template.j2",
    "nested-yml": "nested_yml.j2",
}

# The format a built-in template naturally renders in.
BUILTIN_TEMPLATE_FORMATS: dict[str, str] = {
    "dbt-source": "yml",
    "column-mapping": "yml",
    "json-template": "json",
    "nested-yml": "yml",
}

STANDARD_FORMATS: frozenset[str] = frozenset({"json", "yaml", "yml", "csv"})


class TemplateDefinition(BaseModel):
    """A repo-registered template entry."""

    model_config = ConfigDict(extra="forbid")

    path: str
    default_format: str = "yml"

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Template path cannot be empty")
        return value

    @field_validator("default_format")
    @classmethod
    def _normalize_default_format(cls, value: str) -> str:
        fmt = value.lower().strip()
        if not fmt:
            raise ValueError("default_format cannot be empty.")
        return fmt


class TemplateRegistry(BaseModel):
    """Templates loaded from a repo-local config file."""

    model_config = ConfigDict(extra="forbid")

    templates: dict[str, TemplateDefinition] = Field(default_factory=dict)


def load_macro_paths(start_dir: Path | None = None) -> list[Path]:
    """Return project-registered macro search paths resolved to absolute paths."""
    for directory in _iter_search_directories(start_dir):
        paths = _load_macro_paths_from_directory(directory)
        if paths is not None:
            return paths
    return []


def load_template_registry(
    start_dir: Path | None = None,
) -> tuple[Path, TemplateRegistry] | None:
    """Load the first repo-local template registry found above start_dir."""
    for directory in _iter_search_directories(start_dir):
        registry = _load_registry_from_directory(directory)
        if registry is not None:
            return registry
    return None


def resolve_template_source(
    name_or_path: str, start_dir: Path | None = None
) -> tuple[str, str]:
    """Return template source text and its natural output format."""
    registry = load_template_registry(start_dir=start_dir)
    if registry is not None:
        config_path, loaded = registry
        entry = loaded.templates.get(name_or_path)
        if entry is not None:
            template_path = _resolve_config_template_path(
                entry.path, config_path.parent
            )
            return _read_template_text(template_path), entry.default_format

    if name_or_path in BUILTIN_TEMPLATES:
        package = importlib.resources.files("katalogue.templates")
        source = (package / BUILTIN_TEMPLATES[name_or_path]).read_text(encoding="utf-8")
        return source, BUILTIN_TEMPLATE_FORMATS[name_or_path]

    if looks_like_template_path(name_or_path):
        template_path = Path(name_or_path).expanduser()
        if template_path.suffix != ".j2":
            raise ValueError(
                f"Custom template paths must end in .j2 (got '{name_or_path}')."
            )
        return _read_template_text(template_path), "yml"

    builtins = ", ".join(sorted(BUILTIN_TEMPLATES))
    raise ValueError(
        f"Unknown format '{name_or_path}'. Standard formats: json, table, compact. "
        f"Built-in templates: {builtins}. Register a repo template in "
        "katalogue.toml or pyproject.toml, or provide a path to a .j2 file."
    )


def get_template_default_format(
    name_or_path: str, start_dir: Path | None = None
) -> str:
    """Return the natural output format for a template reference."""
    _, fmt = resolve_template_source(name_or_path, start_dir=start_dir)
    return fmt


def looks_like_template_path(value: str) -> bool:
    return value.endswith(".j2") or "/" in value or "\\" in value


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
) -> tuple[Path, TemplateRegistry] | None:
    katalogue_toml = directory / "katalogue.toml"
    if katalogue_toml.is_file():
        registry = _load_registry_from_file(katalogue_toml, is_pyproject=False)
        if registry is not None:
            return katalogue_toml, registry

    pyproject_toml = directory / "pyproject.toml"
    if pyproject_toml.is_file():
        registry = _load_registry_from_file(pyproject_toml, is_pyproject=True)
        if registry is not None:
            return pyproject_toml, registry

    return None


def _load_registry_from_file(
    path: Path, *, is_pyproject: bool
) -> TemplateRegistry | None:
    data = _load_toml_file(path)
    templates = _extract_templates_section(data, is_pyproject=is_pyproject)
    if templates is None:
        return None
    return TemplateRegistry(templates=templates)


def _load_toml_file(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Could not parse template config {path}: {exc}") from None


def _extract_templates_section(
    data: dict[str, Any], *, is_pyproject: bool
) -> dict[str, TemplateDefinition] | None:
    if is_pyproject:
        tool = data.get("tool")
        if not isinstance(tool, dict):
            return None
        katalogue = tool.get("katalogue")
        if not isinstance(katalogue, dict):
            return None
        templates = katalogue.get("templates")
    else:
        templates = data.get("templates")

    if templates is None:
        return None
    if not isinstance(templates, dict):
        raise ValueError("Template registry must be a table of template definitions.")
    if not templates:
        return None

    return {
        name: TemplateDefinition(**definition) for name, definition in templates.items()
    }


def _resolve_config_template_path(path_value: str, config_dir: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = config_dir / path
    if path.suffix != ".j2":
        raise ValueError(f"Custom template paths must end in .j2 (got '{path_value}').")
    return path


def _read_template_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_macro_paths_from_directory(directory: Path) -> list[Path] | None:
    katalogue_toml = directory / "katalogue.toml"
    if katalogue_toml.is_file():
        raw = _extract_macro_paths(_load_toml_file(katalogue_toml), is_pyproject=False)
        if raw is not None:
            return [_resolve_macro_path(p, katalogue_toml.parent) for p in raw]

    pyproject_toml = directory / "pyproject.toml"
    if pyproject_toml.is_file():
        raw = _extract_macro_paths(_load_toml_file(pyproject_toml), is_pyproject=True)
        if raw is not None:
            return [_resolve_macro_path(p, pyproject_toml.parent) for p in raw]

    return None


def _extract_macro_paths(
    data: dict[str, Any], *, is_pyproject: bool
) -> list[str] | None:
    if is_pyproject:
        section = data.get("tool", {}).get("katalogue", {}).get("macro_paths")
    else:
        section = data.get("macro_paths")
    if section is None:
        return None
    if not isinstance(section, dict):
        raise ValueError("macro_paths must be a table with a 'paths' key.")
    paths = section.get("paths", [])
    if not isinstance(paths, list):
        raise ValueError("macro_paths.paths must be an array of strings.")
    return [str(p) for p in paths]


def _resolve_macro_path(path_str: str, config_dir: Path) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = config_dir / path
    return path.resolve()
