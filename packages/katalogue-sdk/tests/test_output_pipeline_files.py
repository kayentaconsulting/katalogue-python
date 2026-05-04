"""Tests for OutputPipeline — single file writing path."""

import json

import pytest

from katalogue.options import OutputOptions
from katalogue.output import OutputPipeline

_DATA = [{"id": 1, "name": "CRM"}, {"id": 2, "name": "ERP"}]


def test_writes_json_file(tmp_path):
    out = tmp_path / "out.json"
    _, file_path, files = OutputPipeline().process(
        _DATA, OutputOptions(format="json", output_file=str(out))
    )
    assert out.exists()
    assert json.loads(out.read_text()) == _DATA
    assert file_path == str(out)
    assert files == []


def test_dry_run_does_not_create_file(tmp_path):
    out = tmp_path / "out.json"
    _, file_path, _ = OutputPipeline().process(
        _DATA, OutputOptions(format="json", output_file=str(out), dry_run=True)
    )
    assert not out.exists()
    assert file_path == str(out)


def test_overwrite_false_raises_on_existing_file(tmp_path):
    out = tmp_path / "out.json"
    out.write_text("old", encoding="utf-8")
    with pytest.raises(FileExistsError):
        OutputPipeline().process(
            _DATA, OutputOptions(format="json", output_file=str(out), overwrite=False)
        )


def test_overwrite_true_replaces_file(tmp_path):
    out = tmp_path / "out.json"
    out.write_text("old", encoding="utf-8")
    OutputPipeline().process(
        _DATA, OutputOptions(format="json", output_file=str(out), overwrite=True)
    )
    assert json.loads(out.read_text()) == _DATA


def test_missing_parent_dir_created(tmp_path):
    out = tmp_path / "nested" / "dir" / "out.json"
    OutputPipeline().process(_DATA, OutputOptions(format="json", output_file=str(out)))
    assert out.exists()
