"""Tests for katalogue.utils — filter_fields, filter_where, unwrap_list."""

from katalogue.utils import filter_fields, filter_where, unwrap_list


class TestUnwrapList:
    def test_plain_list_unchanged(self):
        data = [{"id": 1}, {"id": 2}]
        assert unwrap_list(data) == data

    def test_single_key_wrapper_dict_unwrapped(self):
        data = {"systems": [{"id": 1}, {"id": 2}]}
        assert unwrap_list(data) == [{"id": 1}, {"id": 2}]

    def test_multi_key_dict_wrapped_in_list(self):
        data = {"a": 1, "b": 2}
        assert unwrap_list(data) == [data]

    def test_non_list_value_wrapped(self):
        assert unwrap_list({"systems": "not-a-list"}) == [{"systems": "not-a-list"}]

    def test_scalar_wrapped_in_list(self):
        assert unwrap_list("hello") == ["hello"]


class TestFilterFields:
    def test_none_fields_returns_data_unchanged(self):
        data = [{"a": 1, "b": 2}]
        assert filter_fields(data, None) is data

    def test_empty_fields_returns_data_unchanged(self):
        data = [{"a": 1, "b": 2}]
        assert filter_fields(data, []) is data

    def test_list_of_dicts_subset(self):
        data = [
            {"id": 1, "name": "A", "extra": "x"},
            {"id": 2, "name": "B", "extra": "y"},
        ]
        result = filter_fields(data, ["id", "name"])
        assert result == [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]

    def test_missing_fields_skipped(self):
        data = [{"id": 1}]
        result = filter_fields(data, ["id", "nonexistent"])
        assert result == [{"id": 1}]

    def test_wrapper_dict_unwrapped_and_filtered(self):
        data = {"systems": [{"system_id": 1, "system_name": "A", "extra": "x"}]}
        result = filter_fields(data, ["system_id", "system_name"])
        assert result == [{"system_id": 1, "system_name": "A"}]

    def test_plain_dict_filtered(self):
        data = {"id": 1, "name": "A", "extra": "x"}
        result = filter_fields(data, ["id", "name"])
        assert result == {"id": 1, "name": "A"}

    def test_empty_list_returns_empty(self):
        assert filter_fields([], ["id"]) == []

    def test_non_dict_non_list_returned_unchanged(self):
        assert filter_fields("raw", ["id"]) == "raw"


class TestFilterWhere:
    _rows = [
        {"dataset_id": "ds-001", "name": "Alpha"},
        {"dataset_id": "ds-002", "name": "Beta"},
        {"dataset_id": "ds-001", "name": "Gamma"},
    ]

    def test_filters_matching_rows(self):
        result = filter_where(self._rows, "dataset_id", "ds-001")
        assert result == [
            {"dataset_id": "ds-001", "name": "Alpha"},
            {"dataset_id": "ds-001", "name": "Gamma"},
        ]

    def test_no_match_returns_empty(self):
        assert filter_where(self._rows, "dataset_id", "ds-999") == []

    def test_unwraps_wrapper_dict(self):
        data = {"fields": self._rows}
        result = filter_where(data, "dataset_id", "ds-002")
        assert result == [{"dataset_id": "ds-002", "name": "Beta"}]

    def test_missing_key_excluded(self):
        rows = [{"id": 1}, {"id": 2, "dataset_id": "ds-001"}]
        result = filter_where(rows, "dataset_id", "ds-001")
        assert result == [{"id": 2, "dataset_id": "ds-001"}]

    def test_integer_value_match(self):
        rows = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
        assert filter_where(rows, "id", 1) == [{"id": 1, "v": "a"}]
