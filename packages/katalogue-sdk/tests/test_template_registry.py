"""Tests for repo-local template registry resolution."""

from __future__ import annotations

from pathlib import Path

from katalogue.options import OutputOptions
from katalogue.output import OutputPipeline
from katalogue.rendering import get_template_extension, load_template, render_template

_HIERARCHICAL_DATA = {
    "resource": "system",
    "system": {"system_id": 1, "system_name": "Finance"},
    "datasource": {"datasource_id": 11, "datasource_name": "Sales"},
    "dataset_group": {
        "dataset_group_id": 21,
        "dataset_group_name": "Public",
        "datasource_id": 11,
    },
    "datasets": [
        {"dataset_id": 31, "dataset_name": "Customers", "dataset_group_id": 21}
    ],
    "fields": [
        {
            "field_id": 41,
            "field_name": "Email",
            "dataset_id": 31,
            "datatype_fullname": "varchar",
        }
    ],
}


def _write_repo_template(repo: Path, name: str, body: str, fmt: str) -> None:
    template_dir = repo / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / name).write_text(body, encoding="utf-8")
    (repo / "katalogue.toml").write_text(
        "\n".join(
            [
                f"[templates.{name.removesuffix('.j2')}]",
                f'path = "templates/{name}"',
                f'default_format = "{fmt}"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_repo_katalogue_toml_overrides_builtin_and_sets_extension(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_repo_template(
        repo,
        "dbt-source.j2",
        "repo: {{ system.system_name }}",
        "yaml",
    )
    workdir = repo / "nested" / "work"
    workdir.mkdir(parents=True)
    monkeypatch.chdir(workdir)

    assert render_template(load_template("dbt-source"), _HIERARCHICAL_DATA) == (
        "repo: Finance"
    )
    assert get_template_extension("dbt-source") == "yaml"

    _, _, written = OutputPipeline().process(
        _HIERARCHICAL_DATA,
        OutputOptions(template="dbt-source", split_by="dataset", output_dir="out"),
        root_resource="system",
    )
    assert written[0].path.endswith(".yaml")


def test_pyproject_registry_is_supported(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    template_dir = repo / "shared"
    template_dir.mkdir()
    (template_dir / "customer.j2").write_text(
        "customer: {{ system.system_name }}", encoding="utf-8"
    )
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[tool.katalogue.templates.customer]",
                'path = "shared/customer.j2"',
                'default_format = "json"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(repo)

    assert render_template(load_template("customer"), _HIERARCHICAL_DATA) == (
        "customer: Finance"
    )
    assert get_template_extension("customer") == "json"


def test_arbitrary_default_format_is_allowed(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_repo_template(repo, "report.j2", "# {{ system.system_name }}", "md")
    monkeypatch.chdir(repo)

    assert get_template_extension("report") == "md"

    _, _, written = OutputPipeline().process(
        _HIERARCHICAL_DATA,
        OutputOptions(template="report", split_by="dataset", output_dir="out"),
        root_resource="system",
    )
    assert written[0].path.endswith(".md")


def test_katalogue_toml_takes_precedence_over_pyproject(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "shared").mkdir()
    (repo / "shared" / "override.j2").write_text("catalogue", encoding="utf-8")
    (repo / "shared" / "project.j2").write_text("project", encoding="utf-8")
    (repo / "katalogue.toml").write_text(
        "\n".join(
            [
                "[templates.override]",
                'path = "shared/override.j2"',
                'default_format = "yaml"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        "\n".join(
            [
                "[tool.katalogue.templates.override]",
                'path = "shared/project.j2"',
                'default_format = "json"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(repo)

    assert render_template(load_template("override"), _HIERARCHICAL_DATA) == "catalogue"
    assert get_template_extension("override") == "yaml"
