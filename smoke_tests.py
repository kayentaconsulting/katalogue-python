#!/usr/bin/env python3
"""
Smoke tests for katalogue-cli and katalogue-sdk.

Runs real commands against a live Katalogue instance and prints their output
to the terminal so you can verify it looks correct. No assertions — just raw output.

Requires credentials:
    KATALOGUE_CLIENT_ID
    KATALOGUE_CLIENT_SECRET
    KATALOGUE_URL           (optional, defaults to demo instance)

Usage:
    uv run python smoke_tests.py
    uv run python smoke_tests.py cli-formats
    uv run python smoke_tests.py cli-templates
    uv run python smoke_tests.py sdk

Sections:
    cli-formats      Format flags on list/get (json, yaml, yml, csv, compact, table)
    cli-get          get commands with --include-children
    cli-templates    --template flag and built-in templates
    cli-conversion   --template + --format (e.g. dbt-source -> json)
    cli-file-output  --output-file and --split-by writing files to disk
    cli-errors       Invalid input — should produce a helpful error message
    sdk              Direct Python SDK calls
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIVIDER = "-" * 70


def section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def run(*args: str, label: str | None = None, truncate: int = 60) -> str:
    """Run `katalogue <args>`, print the command and its output, return stdout."""
    display = label or f"katalogue {' '.join(args)}"
    print(f"\n> {display}")
    print(_DIVIDER)
    proc = subprocess.run(
        ["uv", "run", "katalogue", *args],
        capture_output=True,
        text=True,
    )
    out = proc.stdout
    err = proc.stderr.strip()
    if out:
        lines = out.splitlines()
        if truncate and len(lines) > truncate:
            for line in lines[:truncate]:
                print(line)
            print(f"  ... ({len(lines) - truncate} more lines)")
        else:
            print(out, end="" if out.endswith("\n") else "\n")
    if err:
        print(f"[stderr] {err}")
    if proc.returncode != 0:
        print(f"[exit code: {proc.returncode}]")
    return out


def run_to_file(
    *args: str, path: str, label: str | None = None, preview_lines: int = 20
) -> None:
    """Run a command that writes to a file, then print a preview of the file."""
    display = label or f"katalogue {' '.join(args)}"
    print(f"\n> {display}")
    print(_DIVIDER)
    proc = subprocess.run(
        ["uv", "run", "katalogue", *args],
        capture_output=True,
        text=True,
    )
    if proc.stderr.strip():
        print(f"[stderr] {proc.stderr.strip()}")
    if proc.returncode != 0:
        print(f"[exit code: {proc.returncode}]")
        return
    if not os.path.exists(path):
        print(f"[file not created: {path}]")
        return
    size = os.path.getsize(path)
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    print(f"[written: {path}  ({size} bytes, {len(lines)} lines)]")
    print(_DIVIDER)
    preview = lines[:preview_lines]
    for line in preview:
        print(line, end="")
    if len(lines) > preview_lines:
        print(f"\n  ... ({len(lines) - preview_lines} more lines)")


def run_to_dir(*args: str, directory: str, label: str | None = None) -> None:
    """Run a split command, print the files written."""
    display = label or f"katalogue {' '.join(args)}"
    print(f"\n> {display}")
    print(_DIVIDER)
    proc = subprocess.run(
        ["uv", "run", "katalogue", *args],
        capture_output=True,
        text=True,
    )
    out = proc.stdout.strip()
    if proc.stderr.strip():
        print(f"[stderr] {proc.stderr.strip()}")
    if proc.returncode != 0:
        print(f"[exit code: {proc.returncode}]")
        return
    if out:
        print(out)
    if os.path.isdir(directory):
        files = sorted(os.listdir(directory))
        print(f"\n[{len(files)} file(s) in {directory}]")
        for name in files:
            p = os.path.join(directory, name)
            print(f"  {name}  ({os.path.getsize(p)} bytes)")


def sdk_call(label: str, fn) -> None:
    """Run a Python SDK call, print the label and the result."""
    print(f"\n> SDK: {label}")
    print(_DIVIDER)
    try:
        result = fn()
        if hasattr(result, "output") and result.output:
            lines = result.output.splitlines()
            for line in lines[:60]:
                print(line)
            if len(lines) > 60:
                print(f"  ... ({len(lines) - 60} more lines)")
        elif hasattr(result, "data"):
            text = json.dumps(result.data, indent=2, default=str)
            lines = text.splitlines()
            for line in lines[:60]:
                print(line)
            if len(lines) > 60:
                print(f"  ... ({len(lines) - 60} more lines)")
        else:
            print(repr(result))
    except Exception as exc:
        print(f"[error] {exc}")


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def cli_formats() -> None:
    section("CLI - format flags on list commands")

    run("system", "list", "--format", "table")
    run("system", "list", "--format", "json")
    run("system", "list", "--format", "yaml")
    run("system", "list", "--format", "yml")
    run("system", "list", "--format", "json-compact")
    run("system", "list", "--format", "compact")
    run("system", "list", "--format", "csv")

    run("datasource", "list", "--format", "json")
    run("datasource", "list", "--format", "csv")

    run("dataset", "list", "--format", "json")
    run("dataset", "list", "--format", "csv")

    run("field", "list", "--format", "json")
    run("field", "list", "--format", "csv")

    run("glossary", "list", "--format", "json")


def cli_get() -> None:
    section("CLI - get with --include-children")

    # Discover first system ID
    proc = subprocess.run(
        ["uv", "run", "katalogue", "system", "list", "--format", "json"],
        capture_output=True,
        text=True,
    )
    systems = json.loads(proc.stdout) if proc.stdout else []
    if not systems:
        print("No systems found — skipping get tests.")
        return
    system_id = str(systems[0]["system_id"])
    print(f"\n  Using system_id={system_id}")

    run("system", "get", system_id, "--format", "json")
    run("system", "get", system_id, "--format", "yaml")
    run("system", "get", system_id, "--format", "table")
    run("system", "get", system_id, "--format", "csv")
    run("system", "get", system_id, "--include-children", "--format", "json")
    run("system", "get", system_id, "--include-children", "--format", "yaml")
    run(
        "system",
        "get",
        system_id,
        "--include-children",
        "--format",
        "csv",
        label=f"system get {system_id} --include-children --format csv  (flattens to field rows)",
    )

    proc2 = subprocess.run(
        ["uv", "run", "katalogue", "datasource", "list", "--format", "json"],
        capture_output=True,
        text=True,
    )
    datasources = json.loads(proc2.stdout) if proc2.stdout else []
    if datasources:
        ds_id = str(datasources[0]["datasource_id"])
        print(f"\n  Using datasource_id={ds_id}")
        run("datasource", "get", ds_id, "--format", "json")
        run("datasource", "get", ds_id, "--include-children", "--format", "json")
        run("datasource", "get", ds_id, "--include-children", "--format", "csv")


def cli_templates() -> None:
    section("CLI - --template flag")

    proc = subprocess.run(
        ["uv", "run", "katalogue", "datasource", "list", "--format", "json"],
        capture_output=True,
        text=True,
    )
    datasources = json.loads(proc.stdout) if proc.stdout else []
    if not datasources:
        print("No datasources found — skipping template tests.")
        return
    ds_id = str(datasources[0]["datasource_id"])
    print(f"\n  Using datasource_id={ds_id}")

    run("datasource", "get", ds_id, "--include-children", "--template", "dbt-source")
    run(
        "datasource", "get", ds_id, "--include-children", "--template", "column-mapping"
    )
    run("datasource", "get", ds_id, "--include-children", "--template", "json-template")


def cli_conversion() -> None:
    section("CLI - --template + --format conversion")

    proc = subprocess.run(
        ["uv", "run", "katalogue", "datasource", "list", "--format", "json"],
        capture_output=True,
        text=True,
    )
    datasources = json.loads(proc.stdout) if proc.stdout else []
    if not datasources:
        print("No datasources found — skipping conversion tests.")
        return
    ds_id = str(datasources[0]["datasource_id"])
    print(f"\n  Using datasource_id={ds_id}")

    run(
        "datasource",
        "get",
        ds_id,
        "--include-children",
        "--template",
        "dbt-source",
        "--format",
        "yaml",
        label=f"datasource get {ds_id} --include-children --template dbt-source --format yaml  (pass-through)",
    )
    run(
        "datasource",
        "get",
        ds_id,
        "--include-children",
        "--template",
        "dbt-source",
        "--format",
        "json",
        label=f"datasource get {ds_id} --include-children --template dbt-source --format json  (yaml -> json)",
    )
    run(
        "datasource",
        "get",
        ds_id,
        "--include-children",
        "--template",
        "dbt-source",
        "--format",
        "json-compact",
        label=f"datasource get {ds_id} --include-children --template dbt-source --format json-compact",
    )
    run(
        "datasource",
        "get",
        ds_id,
        "--include-children",
        "--template",
        "json-template",
        "--format",
        "yaml",
        label=f"datasource get {ds_id} --include-children --template json-template --format yaml  (json -> yaml)",
    )


def cli_file_output() -> None:
    section("CLI - writing output to files")

    proc = subprocess.run(
        ["uv", "run", "katalogue", "system", "list", "--format", "json"],
        capture_output=True,
        text=True,
    )
    systems = json.loads(proc.stdout) if proc.stdout else []
    if not systems:
        print("No systems found — skipping file output tests.")
        return
    system_id = str(systems[0]["system_id"])
    print(f"\n  Using system_id={system_id}")

    with tempfile.TemporaryDirectory() as tmp:
        json_file = os.path.join(tmp, "output.json")
        run_to_file(
            "system",
            "get",
            system_id,
            "--include-children",
            "--format",
            "json",
            "--output-file",
            json_file,
            path=json_file,
            label=f"system get {system_id} --include-children --format json --output-file output.json",
        )

        yaml_file = os.path.join(tmp, "output.yaml")
        run_to_file(
            "system",
            "get",
            system_id,
            "--include-children",
            "--format",
            "yaml",
            "--output-file",
            yaml_file,
            path=yaml_file,
            label=f"system get {system_id} --include-children --format yaml --output-file output.yaml",
        )

        csv_file = os.path.join(tmp, "output.csv")
        run_to_file(
            "system",
            "get",
            system_id,
            "--include-children",
            "--format",
            "csv",
            "--output-file",
            csv_file,
            path=csv_file,
            label=f"system get {system_id} --include-children --format csv --output-file output.csv",
        )

        tmpl_file = os.path.join(tmp, "dbt_source.yaml")
        run_to_file(
            "system",
            "get",
            system_id,
            "--include-children",
            "--template",
            "dbt-source",
            "--output-file",
            tmpl_file,
            path=tmpl_file,
            label=f"system get {system_id} --include-children --template dbt-source --output-file dbt_source.yaml",
        )

        split_dir = os.path.join(tmp, "split_by_dataset")
        run_to_dir(
            "system",
            "get",
            system_id,
            "--include-children",
            "--format",
            "json",
            "--split-by",
            "dataset",
            "--output-dir",
            split_dir,
            directory=split_dir,
            label=f"system get {system_id} --include-children --format json --split-by dataset --output-dir split_by_dataset/",
        )

        tmpl_split_dir = os.path.join(tmp, "split_dbt")
        run_to_dir(
            "system",
            "get",
            system_id,
            "--include-children",
            "--template",
            "dbt-source",
            "--split-by",
            "dataset",
            "--output-dir",
            tmpl_split_dir,
            directory=tmpl_split_dir,
            label=f"system get {system_id} --include-children --template dbt-source --split-by dataset --output-dir split_dbt/",
        )


def cli_errors() -> None:
    section("CLI - invalid input (each should print an error message)")

    run(
        "system",
        "list",
        "--format",
        "xlsx",
        label="system list --format xlsx  (unknown format -> usage error)",
    )
    run(
        "system",
        "list",
        "--format",
        "dbt-source",
        label="system list --format dbt-source  (template name in --format -> usage error)",
    )
    run(
        "system",
        "get",
        "1",
        "--include-children",
        "--template",
        "dbt-source",
        "--format",
        "table",
        label="system get 1 --include-children --template dbt-source --format table  (incompatible -> error)",
    )
    run(
        "system",
        "get",
        "1",
        "--split-by",
        "dataset",
        "--output-dir",
        "/tmp/x",
        label="system get 1 --split-by dataset (without --include-children -> error)",
    )


def sdk_section() -> None:
    section("SDK - direct Python calls")

    from katalogue import GetOptions, KatalogueClient, OutputOptions

    client = KatalogueClient()

    sdk_call("KatalogueClient() - type", lambda: type(client).__name__)
    sdk_call("client.get('system')", lambda: client.get("system"))
    sdk_call(
        "client.get('system', format=json)",
        lambda: client.get("system", GetOptions(output=OutputOptions(format="json"))),
    )
    sdk_call(
        "client.get('system', format=yaml)",
        lambda: client.get("system", GetOptions(output=OutputOptions(format="yaml"))),
    )
    sdk_call(
        "client.get('system', format=yml)",
        lambda: client.get("system", GetOptions(output=OutputOptions(format="yml"))),
    )
    sdk_call(
        "client.get('system', format=json-compact)",
        lambda: client.get(
            "system", GetOptions(output=OutputOptions(format="json-compact"))
        ),
    )
    sdk_call(
        "client.get('system', format=csv)",
        lambda: client.get("system", GetOptions(output=OutputOptions(format="csv"))),
    )
    sdk_call("client.get('datasource')", lambda: client.get("datasource"))
    sdk_call(
        "client.get('field', format=csv)",
        lambda: client.get("field", GetOptions(output=OutputOptions(format="csv"))),
    )

    systems = client.get("system").data or []
    if not isinstance(systems, list) or not systems:
        print("\n  No systems found — skipping hierarchical SDK tests.")
        return
    system_id = systems[0]["system_id"]
    print(f"\n  Using system_id={system_id}")

    sdk_call(
        f"client.get('system', id={system_id}, include_children=True)",
        lambda: client.get(
            "system", GetOptions(resource_id=system_id, include_children=True)
        ),
    )
    sdk_call(
        f"client.get('system', id={system_id}, include_children=True, format=csv)",
        lambda: client.get(
            "system",
            GetOptions(
                resource_id=system_id,
                include_children=True,
                output=OutputOptions(format="csv"),
            ),
        ),
    )
    sdk_call(
        f"client.get('system', id={system_id}, include_children=True, template=dbt-source)",
        lambda: client.get(
            "system",
            GetOptions(
                resource_id=system_id,
                include_children=True,
                output=OutputOptions(template="dbt-source"),
            ),
        ),
    )
    sdk_call(
        f"client.get('system', id={system_id}, include_children=True, template=dbt-source, format=json)",
        lambda: client.get(
            "system",
            GetOptions(
                resource_id=system_id,
                include_children=True,
                output=OutputOptions(template="dbt-source", format="json"),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

SECTIONS = {
    "cli-formats": cli_formats,
    "cli-get": cli_get,
    "cli-templates": cli_templates,
    "cli-conversion": cli_conversion,
    "cli-file-output": cli_file_output,
    "cli-errors": cli_errors,
    "sdk": sdk_section,
}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "section",
        nargs="?",
        choices=[*SECTIONS, "all"],
        default="all",
        help="Which section to run (default: all)",
    )
    args = parser.parse_args()

    missing = [
        v
        for v in ("KATALOGUE_CLIENT_ID", "KATALOGUE_CLIENT_SECRET")
        if not os.getenv(v)
    ]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        print(
            "Set KATALOGUE_CLIENT_ID, KATALOGUE_CLIENT_SECRET (and optionally KATALOGUE_URL)."
        )
        sys.exit(1)

    to_run = (
        list(SECTIONS.values()) if args.section == "all" else [SECTIONS[args.section]]
    )
    for fn in to_run:
        fn()

    print()


if __name__ == "__main__":
    main()
