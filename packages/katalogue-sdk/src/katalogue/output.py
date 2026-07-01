"""OutputPipeline — render, write, and split catalog export results."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from katalogue.formatters import format_resultset
from katalogue.options import OutputOptions
from katalogue.rendering import (
    auto_filename,
    get_template_extension,
    load_template,
    render_filename,
    render_template,
)
from katalogue.results import WrittenFile

# Which split_by values are valid for each root resource.
_VALID_SPLITS: dict[str, frozenset[str]] = {
    "system": frozenset({"system", "datasource", "dataset_group", "dataset"}),
    "datasource": frozenset({"datasource", "dataset_group", "dataset"}),
    "dataset_group": frozenset({"dataset_group", "dataset"}),
    "dataset": frozenset({"dataset"}),
    "glossary": frozenset(),
    "business_term": frozenset(),
    "field_description": frozenset(),
}

_YAML_FMTS: frozenset[str] = frozenset({"yaml", "yml"})
_JSON_FMTS: frozenset[str] = frozenset({"json", "json-compact", "compact"})


def _effective_extension(template: str | None, fmt: str | None) -> str:
    """Return the file extension for auto-generated filenames."""
    if fmt and fmt in _YAML_FMTS:
        return "yaml"
    if fmt == "json":
        return "json"
    if fmt in ("json-compact", "compact"):
        return "json"
    if fmt == "csv":
        return "csv"
    if template:
        return get_template_extension(template)
    return "txt"


class OutputPipeline:
    def process(
        self,
        data: Any,
        options: OutputOptions,
        root_resource: str | None = None,
    ) -> tuple[str | None, str | None, list[WrittenFile]]:
        """Render data and optionally write to file(s).

        Returns (output, output_file, output_files).
        """
        template = options.template
        fmt = options.format

        if template and fmt == "table":
            raise ValueError(
                "table format cannot be combined with --template; "
                "omit --format or choose json, yaml, or csv."
            )

        if not template and not fmt:
            return None, None, []

        if options.split_by:
            return self._process_split(data, template, fmt, options, root_resource)

        rendered = self._render_output(data, template, fmt)

        if options.output_file:
            return self._write_single_file(rendered, options)

        return rendered, None, []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render_output(self, data: Any, template: str | None, fmt: str | None) -> str:
        if template:
            if not isinstance(data, dict):
                raise ValueError(
                    "Template rendering requires dict-shaped (hierarchical) data."
                )
            rendered = self._render_template(data, template)
            if fmt:
                rendered = self._convert_rendered(
                    rendered, template=template, to_fmt=fmt
                )
            return rendered
        return self._render_format(data, fmt)  # type: ignore[arg-type]

    def _render_template(self, data: dict[str, Any], template: str) -> str:
        tmpl = load_template(template)
        return render_template(tmpl, data)

    def _render_format(self, data: Any, fmt: str) -> str:
        result = format_resultset(data, fmt)
        return result if isinstance(result, str) else ""

    def _convert_rendered(self, text: str, *, template: str, to_fmt: str) -> str:
        """Convert rendered template text to another serialization format."""
        natural = get_template_extension(template)  # "yml" or "json"

        if to_fmt in _YAML_FMTS and natural in ("yml", "yaml"):
            return text  # already YAML

        if to_fmt == "json" and natural in ("yml", "yaml"):
            parsed = yaml.safe_load(text)
            return json.dumps(parsed, indent=2, default=str)

        if to_fmt in ("json-compact", "compact") and natural in ("yml", "yaml"):
            parsed = yaml.safe_load(text)
            return json.dumps(parsed, separators=(",", ":"), default=str)

        if to_fmt in _YAML_FMTS and natural == "json":
            parsed = json.loads(text)
            return yaml.dump(
                parsed, allow_unicode=True, sort_keys=False, default_flow_style=False
            )

        if to_fmt == "json" and natural == "json":
            return text  # already JSON

        raise ValueError(
            f"Cannot convert {template!r} output (natural format: .{natural}) "
            f"to format {to_fmt!r}. Supported conversions: yaml↔json, yaml→json-compact."
        )

    def _write_single_file(
        self, content: str, options: OutputOptions
    ) -> tuple[str, str, list[WrittenFile]]:
        path = Path(options.output_file)  # type: ignore[arg-type]
        if options.dry_run:
            return content, str(path), []
        if path.exists() and not options.overwrite:
            raise FileExistsError(f"Output file already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return content, str(path), []

    def _process_split(
        self,
        data: dict[str, Any],
        template: str | None,
        fmt: str | None,
        options: OutputOptions,
        root_resource: str | None,
    ) -> tuple[None, None, list[WrittenFile]]:
        level = str(options.split_by).replace("-", "_")
        resource = root_resource or data.get("resource") or ""

        valid = _VALID_SPLITS.get(resource, frozenset())
        if level not in valid:
            valid_str = ", ".join(sorted(valid)) or "none"
            raise ValueError(
                f"Invalid split_by '{level}' for {resource!r}. Valid: {valid_str}."
            )

        contexts = _build_split_contexts(data, resource, level)
        output_dir = Path(options.output_dir)  # type: ignore[arg-type]
        ext = _effective_extension(template, fmt)

        if not options.dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

        written: list[WrittenFile] = []
        seen: dict[str, int] = {}

        for unit, context in contexts:
            content = self._render_output(context, template, fmt)

            if options.filename_template:
                filename = render_filename(options.filename_template, context)
            else:
                filename = auto_filename(context, split_by=level, extension=ext)

            filename = _dedup_filename(filename, seen)
            file_path = output_dir / filename

            if not options.dry_run:
                if file_path.exists() and not options.overwrite:
                    raise FileExistsError(f"Output file already exists: {file_path}")
                file_path.write_text(content, encoding="utf-8")

            split_value = unit.get(f"{level}_name") or unit.get(f"{level}_id")
            written.append(
                WrittenFile(
                    path=str(file_path),
                    split_key=level,
                    split_value=split_value,
                    resource_type=level,
                )
            )

        return None, None, written


def _dedup_filename(filename: str, seen: dict[str, int]) -> str:
    if filename not in seen:
        seen[filename] = 0
        return filename
    seen[filename] += 1
    stem = Path(filename).stem
    ext = Path(filename).suffix
    return f"{stem}-{seen[filename]}{ext}"


# ---------------------------------------------------------------------------
# Context builders (adapted from renderer/context.py)
# ---------------------------------------------------------------------------


def _build_split_contexts(
    data: dict[str, Any],
    resource: str,
    level: str,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return (split_unit, render_context) pairs for each split item."""
    if level == "system":
        ctx = deepcopy(data)
        return [(ctx.get("system", {}), ctx)]
    if level == "datasource":
        return [(c.get("datasource", {}), c) for c in _split_by_datasource(data)]
    if level == "dataset_group":
        return [(c.get("dataset_group", {}), c) for c in _split_by_dataset_group(data)]
    if level == "dataset":
        return [(c.get("dataset", {}), c) for c in _split_by_dataset(data)]
    return []


def _as_list(data: dict[str, Any], plural: str, singular: str) -> list[dict[str, Any]]:
    if isinstance(data.get(plural), list):
        return data[plural]
    if isinstance(data.get(singular), dict):
        return [data[singular]]
    return []


def _split_by_datasource(data: dict[str, Any]) -> list[dict[str, Any]]:
    system = data.get("system", {})
    datasources = _as_list(data, "datasources", "datasource")
    groups = data.get("dataset_groups", [])
    datasets = data.get("datasets", [])
    fields = data.get("fields", [])
    result = []
    for ds in datasources:
        ds_id = ds.get("datasource_id")
        my_groups = [g for g in groups if g.get("datasource_id") == ds_id]
        group_ids = {g.get("dataset_group_id") for g in my_groups}
        my_datasets = [d for d in datasets if d.get("dataset_group_id") in group_ids]
        ds_ids = {d.get("dataset_id") for d in my_datasets}
        result.append(
            {
                "resource": "datasource",
                "system": system,
                "datasource": ds,
                "dataset_groups": my_groups,
                "datasets": my_datasets,
                "fields": [f for f in fields if f.get("dataset_id") in ds_ids],
            }
        )
    return result


def _split_by_dataset_group(data: dict[str, Any]) -> list[dict[str, Any]]:
    system = data.get("system", {})
    datasources = _as_list(data, "datasources", "datasource")
    groups = _as_list(data, "dataset_groups", "dataset_group")
    datasets = data.get("datasets", [])
    fields = data.get("fields", [])
    result = []
    for group in groups:
        group_id = group.get("dataset_group_id")
        ds_id = group.get("datasource_id")
        datasource = next(
            (d for d in datasources if d.get("datasource_id") == ds_id), {}
        )
        my_datasets = [d for d in datasets if d.get("dataset_group_id") == group_id]
        dataset_ids = {d.get("dataset_id") for d in my_datasets}
        result.append(
            {
                "resource": "dataset_group",
                "system": system,
                "datasource": datasource,
                "dataset_group": group,
                "datasets": my_datasets,
                "fields": [f for f in fields if f.get("dataset_id") in dataset_ids],
            }
        )
    return result


def _split_by_dataset(data: dict[str, Any]) -> list[dict[str, Any]]:
    system = data.get("system", {})
    datasources = _as_list(data, "datasources", "datasource")
    groups = _as_list(data, "dataset_groups", "dataset_group")
    datasets = _as_list(data, "datasets", "dataset")
    fields = data.get("fields", [])
    result = []
    for dataset in datasets:
        dataset_id = dataset.get("dataset_id")
        group_id = dataset.get("dataset_group_id")
        group = next((g for g in groups if g.get("dataset_group_id") == group_id), {})
        ds_id = group.get("datasource_id")
        datasource = next(
            (d for d in datasources if d.get("datasource_id") == ds_id), {}
        )
        result.append(
            {
                "resource": "dataset",
                "system": system,
                "datasource": datasource,
                "dataset_group": group,
                "dataset": dataset,
                "datasets": [dataset],
                "fields": [f for f in fields if f.get("dataset_id") == dataset_id],
            }
        )
    return result
