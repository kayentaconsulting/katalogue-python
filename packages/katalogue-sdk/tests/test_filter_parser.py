import pytest

from katalogue.filters import Filter, FilterParser, parse_filters


# --- helpers ---


def _p(s: str) -> Filter:
    return FilterParser().parse(s)[0]  # type: ignore[index]


# --- per-operator parsing ---


def test_eq_unquoted() -> None:
    f = _p("name=Hello")
    assert f.path == "name"
    assert f.operator == "="
    assert f.value == "Hello"


def test_neq() -> None:
    f = _p('system.name!="CRM"')
    assert f.path == "system.name"
    assert f.operator == "!="
    assert f.value == "CRM"


def test_gt() -> None:
    f = _p("id>10")
    assert f.path == "id"
    assert f.operator == ">"
    assert f.value == 10


def test_gte() -> None:
    f = _p("id>=10")
    assert f.operator == ">="
    assert f.value == 10


def test_lt() -> None:
    f = _p("id<5")
    assert f.operator == "<"
    assert f.value == 5


def test_lte() -> None:
    f = _p("id<=5")
    assert f.operator == "<="
    assert f.value == 5


def test_in_operator() -> None:
    f = _p("type in db,api")
    assert f.path == "type"
    assert f.operator == "in"
    assert f.value == ["db", "api"]


def test_not_in_operator() -> None:
    f = _p("type not-in db,api")
    assert f.operator == "not-in"
    assert f.value == ["db", "api"]


def test_contains_operator() -> None:
    f = _p("description contains pii")
    assert f.path == "description"
    assert f.operator == "contains"
    assert f.value == "pii"


def test_startswith_operator() -> None:
    f = _p("description startswith pii")
    assert f.path == "description"
    assert f.operator == "startswith"
    assert f.value == "pii"


def test_endswith_operator() -> None:
    f = _p("description endswith pii")
    assert f.path == "description"
    assert f.operator == "endswith"
    assert f.value == "pii"


# --- dotted path preserved ---


def test_dotted_path_preserved() -> None:
    f = _p("datasets.fields.name=x")
    assert f.path == "datasets.fields.name"


# --- type coercion ---


def test_coerce_true() -> None:
    assert _p("is_pii=true").value is True


def test_coerce_false() -> None:
    assert _p("is_pii=false").value is False


def test_coerce_true_case_insensitive() -> None:
    assert _p("flag=TRUE").value is True


def test_coerce_int() -> None:
    assert _p("id=42").value == 42
    assert isinstance(_p("id=42").value, int)


def test_quoted_int_stays_string() -> None:
    assert _p('id="42"').value == "42"
    assert isinstance(_p('id="42"').value, str)


def test_unquoted_multi_word_value() -> None:
    f = _p("name=hello world")
    assert f.value == "hello world"


# --- quoting ---


def test_double_quoted_value() -> None:
    f = _p('system.name="My System"')
    assert f.value == "My System"


def test_single_quoted_value() -> None:
    f = _p("system.name='My System'")
    assert f.value == "My System"


def test_quoted_value_with_embedded_operator() -> None:
    f = _p('name="x=y"')
    assert f.value == "x=y"


# --- in / not-in list coercion ---


def test_in_int_list() -> None:
    f = _p("id in 1,2,3")
    assert f.value == [1, 2, 3]


def test_in_single_element() -> None:
    f = _p("type in db")
    assert f.value == ["db"]


def test_in_mixed_types_not_coerced_to_int_when_mixed() -> None:
    f = _p("tag in a,b,c")
    assert f.value == ["a", "b", "c"]


# --- error cases ---


def test_empty_string_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        FilterParser().parse("")


def test_no_operator_raises() -> None:
    with pytest.raises(ValueError):
        FilterParser().parse("foo")


def test_empty_path_raises() -> None:
    with pytest.raises(ValueError, match="path"):
        FilterParser().parse("=value")


def test_empty_value_raises_for_eq() -> None:
    with pytest.raises(ValueError, match="value"):
        FilterParser().parse("name=")


# --- pass-through ---


def test_parse_none_returns_none() -> None:
    assert FilterParser().parse(None) is None


def test_parse_filter_list_passthrough() -> None:
    f = Filter(path="x", operator="=", value=1)
    result = FilterParser().parse([f])
    assert result == [f]


def test_parse_list_of_strings() -> None:
    result = FilterParser().parse(["a=1", "b=2"])
    assert result is not None
    assert len(result) == 2
    assert result[0].path == "a"
    assert result[1].path == "b"


def test_parse_single_string() -> None:
    result = FilterParser().parse("x=y")
    assert result is not None
    assert len(result) == 1


# --- convenience function ---


def test_parse_filters_function() -> None:
    result = parse_filters("name=foo")
    assert result is not None
    assert result[0].value == "foo"


def test_parse_filters_none() -> None:
    assert parse_filters(None) is None


# --- determinism ---


def test_determinism() -> None:
    s = 'system.name="CRM"'
    assert FilterParser().parse(s) == FilterParser().parse(s)
