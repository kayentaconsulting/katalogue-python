import pytest
from pydantic import ValidationError

from katalogue.filters import Filter


def test_filter_constructs() -> None:
    f = Filter(path="x", operator="=", value="a")
    assert f.path == "x"
    assert f.operator == "="
    assert f.value == "a"


def test_filter_dotted_path() -> None:
    f = Filter(path="system.name", operator="!=", value="CRM")
    assert f.path == "system.name"


def test_filter_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Filter(path="x", operator="=", value="a", unknown="bad")  # type: ignore[call-arg]


def test_filter_empty_path_rejected() -> None:
    with pytest.raises(ValidationError):
        Filter(path="", operator="=", value="a")


@pytest.mark.parametrize(
    "op",
    ["=", "!=", ">", ">=", "<", "<=", "in", "not-in", "contains"],
)
def test_filter_all_operators_accepted(op: str) -> None:
    f = Filter(path="x", operator=op, value=1)  # type: ignore[arg-type]
    assert f.operator == op


def test_filter_invalid_operator_rejected() -> None:
    with pytest.raises(ValidationError):
        Filter(path="x", operator="LIKE", value="a")  # type: ignore[arg-type]


def test_filter_frozen_raises_on_assignment() -> None:
    f = Filter(path="x", operator="=", value="a")
    with pytest.raises(ValidationError):
        f.path = "y"  # type: ignore[misc]


def test_filter_accepts_list_value() -> None:
    f = Filter(path="x", operator="in", value=["a", "b"])
    assert f.value == ["a", "b"]
