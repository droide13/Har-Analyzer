from app.shared.aggregation import describe_value, group_by_name


def test_group_by_name_preserves_first_seen_order() -> None:
    records = [
        {"Name": "b", "v": 1},
        {"Name": "a", "v": 2},
        {"Name": "b", "v": 3},
    ]
    groups = group_by_name(records)
    assert list(groups.keys()) == ["b", "a"]
    assert groups["b"] == [{"Name": "b", "v": 1}, {"Name": "b", "v": 3}]


def test_describe_value_single_vs_multiple() -> None:
    assert describe_value({"abc123"}) == "abc123"
    assert describe_value({""}) == "(empty)"
    assert describe_value({"a", "b"}) == "Multiple values (2)"
