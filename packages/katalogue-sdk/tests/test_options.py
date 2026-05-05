import pytest
from pydantic import ValidationError

from katalogue.filters import Filter
from katalogue.options import GetOptions, OutputOptions


def test_output_options_defaults() -> None:
    o = OutputOptions()
    assert o.format is None
    assert o.template is None
    assert o.output_file is None
    assert o.output_dir is None
    assert o.split_by is None
    assert o.filename_template is None
    assert o.overwrite is False
    assert o.dry_run is False


def test_get_options_defaults() -> None:
    g = GetOptions()
    assert g.resource_id is None
    assert g.parent_id is None
    assert g.filters is None
    assert g.properties is None
    assert g.sort is None
    assert g.include_children is False
    assert g.format_descriptions_as_text is False
    assert isinstance(g.output, OutputOptions)


def test_output_options_extra_rejected() -> None:
    with pytest.raises(ValidationError):
        OutputOptions(unknown="bad")  # type: ignore[call-arg]


def test_get_options_extra_rejected() -> None:
    with pytest.raises(ValidationError):
        GetOptions(unknown="bad")  # type: ignore[call-arg]


def test_split_by_requires_include_children() -> None:
    with pytest.raises(ValidationError, match="split_by requires include_children"):
        GetOptions(output=OutputOptions(split_by="dataset", output_dir="/out"))


def test_split_by_with_output_file_rejected() -> None:
    with pytest.raises(
        ValidationError, match="split_by cannot be combined with output_file"
    ):
        GetOptions(
            include_children=True,
            output=OutputOptions(split_by="dataset", output_file="out.json"),
        )


def test_split_by_without_output_dir_rejected() -> None:
    with pytest.raises(ValidationError, match="split_by requires output_dir"):
        GetOptions(
            include_children=True,
            output=OutputOptions(split_by="dataset"),
        )


def test_output_file_and_output_dir_mutually_exclusive() -> None:
    with pytest.raises(
        ValidationError, match="output_file and output_dir are mutually exclusive"
    ):
        GetOptions(output=OutputOptions(output_file="f.json", output_dir="/out"))


def test_filters_accepts_none() -> None:
    g = GetOptions(filters=None)
    assert g.filters is None


def test_filters_accepts_str() -> None:
    g = GetOptions(filters='name="foo"')
    assert g.filters == 'name="foo"'


def test_filters_accepts_list_of_str() -> None:
    g = GetOptions(filters=['name="foo"', 'type!="bar"'])
    assert g.filters == ['name="foo"', 'type!="bar"']


def test_filters_accepts_list_of_filter() -> None:
    f = Filter(path="name", operator="=", value="foo")
    g = GetOptions(filters=[f])
    assert g.filters == [f]


def test_model_dump_round_trip() -> None:
    g = GetOptions(resource_id=1, include_children=True)
    d = g.model_dump()
    g2 = GetOptions(**d)
    assert g2.resource_id == 1
    assert g2.include_children is True


def test_model_dump_json_round_trip() -> None:
    g = GetOptions(resource_id="abc")
    j = g.model_dump_json()
    g2 = GetOptions.model_validate_json(j)
    assert g2.resource_id == "abc"
