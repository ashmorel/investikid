from app.services.llm_json import extract_json_list


def test_top_level_list_returned_as_is():
    assert extract_json_list([{"a": 1}]) == [{"a": 1}]


def test_object_wrapped_under_any_key():
    assert extract_json_list({"proposed_modules": [{"title": "x"}]}) == [{"title": "x"}]
    assert extract_json_list({"tips": [1, 2]}) == [1, 2]
    assert extract_json_list({"meta": "ignored", "items": [9]}) == [9]


def test_non_list_non_dict_yields_empty():
    assert extract_json_list("not json") == []
    assert extract_json_list(42) == []
    assert extract_json_list({"no": "list", "here": 1}) == []
