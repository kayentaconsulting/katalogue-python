import pytest
from pydantic import ValidationError

from katalogue.results import CatalogResult, WrittenFile


def test_written_file_constructs() -> None:
    wf = WrittenFile(path="out/file.json")
    assert wf.path == "out/file.json"
    assert wf.split_key is None
    assert wf.split_value is None
    assert wf.resource_type is None


def test_written_file_extra_rejected() -> None:
    with pytest.raises(ValidationError):
        WrittenFile(path="x", unknown="bad")  # type: ignore[call-arg]


def test_written_file_with_all_fields() -> None:
    wf = WrittenFile(
        path="out/crm.json",
        split_key="system",
        split_value="CRM",
        resource_type="system",
    )
    assert wf.split_value == "CRM"
    assert wf.resource_type == "system"


def test_catalog_result_constructs_with_defaults() -> None:
    r = CatalogResult(data={"id": 1})
    assert r.data == {"id": 1}
    assert r.raw is None
    assert r.output is None
    assert r.output_file is None
    assert r.output_files == []
    assert r.metadata == {}


def test_catalog_result_output_files_default_not_shared() -> None:
    r1 = CatalogResult(data=None)
    r2 = CatalogResult(data=None)
    r1.output_files.append(WrittenFile(path="x"))
    assert r2.output_files == []


def test_catalog_result_extra_rejected() -> None:
    with pytest.raises(ValidationError):
        CatalogResult(data=None, unknown="bad")  # type: ignore[call-arg]


def test_catalog_result_json_round_trip() -> None:
    r = CatalogResult(
        data=[{"id": 1}],
        output="hello",
        metadata={"strategy": "list"},
    )
    j = r.model_dump_json()
    r2 = CatalogResult.model_validate_json(j)
    assert r2.output == "hello"
    assert r2.metadata == {"strategy": "list"}


def test_catalog_result_accepts_list_data() -> None:
    r = CatalogResult(data=[{"id": 1}, {"id": 2}])
    assert len(r.data) == 2


def test_catalog_result_accepts_none_data() -> None:
    r = CatalogResult(data=None)
    assert r.data is None
