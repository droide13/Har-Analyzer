from app.shared.json_body import MAX_BODY_CHARS, MAX_LEAVES_PER_BODY, flatten_json, parse_json_body


def test_parse_json_body_accepts_object_and_array_rejects_everything_else() -> None:
    assert parse_json_body('{"a": 1}') == {"a": 1}
    assert parse_json_body("[1, 2]") == [1, 2]
    assert parse_json_body("") is None
    assert parse_json_body("<html></html>") is None
    assert parse_json_body("not json at all") is None
    assert parse_json_body("{not valid json") is None


def test_parse_json_body_rejects_bodies_over_the_size_cap() -> None:
    huge = '{"a": "' + ("x" * MAX_BODY_CHARS) + '"}'
    assert len(huge) > MAX_BODY_CHARS
    assert parse_json_body(huge) is None

    just_under = '{"a": "' + ("x" * 10) + '"}'
    assert parse_json_body(just_under) == {"a": "x" * 10}


def test_flatten_json_produces_dotted_paths_for_nested_objects() -> None:
    parsed = {"fms_params": {"fms_uid2": "A4AAAE...", "fms_userid": "c293b192-..."}}
    assert set(flatten_json(parsed)) == {
        ("fms_params.fms_uid2", "A4AAAE..."),
        ("fms_params.fms_userid", "c293b192-..."),
    }


def test_flatten_json_indexes_arrays_and_drops_nulls() -> None:
    parsed = {"eids": [{"source": "uid2.com", "id": "abc"}, None]}
    assert set(flatten_json(parsed)) == {
        ("eids[0].source", "uid2.com"),
        ("eids[0].id", "abc"),
    }


def test_flatten_json_stops_at_max_leaves_for_a_huge_flat_array() -> None:
    # A product catalog / config dump shape: one huge flat array, not an
    # identity payload -- this is exactly what used to blow up processing
    # and the rendered response with no cap at all.
    parsed = {"items": [{"id": str(i)} for i in range(10_000)]}
    result = flatten_json(parsed)
    assert len(result) == MAX_LEAVES_PER_BODY


def test_flatten_json_respects_a_custom_max_leaves() -> None:
    parsed = {"a": "1", "b": "2", "c": "3"}
    assert len(flatten_json(parsed, max_leaves=2)) == 2
