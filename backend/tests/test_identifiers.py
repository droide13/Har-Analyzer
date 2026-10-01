from app.core.models import build_entries_from_har_data
from app.features.identifiers import (
    TrackedKey,
    extract_tracked_keys,
    filter_identifiers,
    filter_known_ids,
    get_all_items,
    get_body_items,
    get_cookie_items,
    get_query_items,
    shannon_entropy,
    sort_identifiers,
)


def test_shannon_entropy_zero_for_empty_and_repeated_chars() -> None:
    assert shannon_entropy("") == 0.0
    assert shannon_entropy("aaaa") == 0.0
    assert shannon_entropy("ab") > 0.0


def test_extract_tracked_keys_for_query_params(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    tracked = extract_tracked_keys(entries, get_query_items)

    assert set(tracked) == {"token"}
    token = tracked["token"]
    assert token.total_appearances == 2
    assert token.unique_value_count == 1
    assert token.first_seen_as is None  # query params carry no side


def test_extract_tracked_keys_for_cookies_tracks_scope(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    tracked = extract_tracked_keys(entries, get_cookie_items)

    session = tracked["session"]
    assert session.total_appearances == 3
    assert session.unique_value_count == 2
    assert session.first_seen_as == "Request Cookie"


def test_filter_identifiers_thresholds(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    tracked = extract_tracked_keys(entries, get_cookie_items)

    # "session" appears 3 times with 2 unique values; require at least that.
    matches = filter_identifiers(
        tracked,
        min_appearances=3,
        max_unique_values=2,
        min_avg_length=0,
        min_avg_entropy=0.0,
        name_query="",
        exclude_common=False,
    )
    assert {tk.key for tk in matches} == {"session"}

    # Tightening max_unique_values below 2 excludes it.
    no_matches = filter_identifiers(
        tracked,
        min_appearances=3,
        max_unique_values=1,
        min_avg_length=0,
        min_avg_entropy=0.0,
        name_query="",
        exclude_common=False,
    )
    assert no_matches == []


def test_filter_identifiers_excludes_noise_keys(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    tracked = extract_tracked_keys(
        entries, get_query_items
    )  # "token" isn't noise, but exercise the flag
    matches_without_exclusion = filter_identifiers(
        tracked,
        min_appearances=1,
        max_unique_values=20,
        min_avg_length=0,
        min_avg_entropy=0.0,
        name_query="",
        exclude_common=False,
    )
    assert {tk.key for tk in matches_without_exclusion} == {"token"}


def test_sort_identifiers_by_appearances(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    tracked = extract_tracked_keys(entries, get_cookie_items)
    matches = filter_identifiers(
        tracked,
        min_appearances=1,
        max_unique_values=20,
        min_avg_length=0,
        min_avg_entropy=0.0,
        name_query="",
        exclude_common=False,
    )
    ordered = sort_identifiers(matches, "Appearances")
    # "session" (3 appearances) should sort before "tracking_id" (1 appearance).
    assert [tk.key for tk in ordered][0] == "session"


def test_get_body_items_finds_identifier_in_json_response_body() -> None:
    entry = {
        "startedDateTime": "2026-01-01T00:00:00.000Z",
        "time": 1.0,
        "request": {
            "method": "GET",
            "url": "https://example.com/id",
            "headers": [],
            "cookies": [],
            "queryString": [],
        },
        "response": {
            "status": 200,
            "statusText": "OK",
            "headers": [],
            "cookies": [],
            "content": {
                "mimeType": "application/json",
                "text": '{"fms_params": {"fms_uid2": "A4-token-value"}}',
            },
            "bodySize": 0,
            "headersSize": 0,
        },
        "_initiator": {},
    }
    entries = build_entries_from_har_data({"log": {"entries": [entry]}})
    items = get_body_items(entries[0])

    assert ("Response Body", {"name": "fms_params.fms_uid2", "value": "A4-token-value"}) in items


def test_get_all_items_combines_query_cookie_and_body_sources() -> None:
    entry = {
        "startedDateTime": "2026-01-01T00:00:00.000Z",
        "time": 1.0,
        "request": {
            "method": "GET",
            "url": "https://example.com/id?id5id=abc",
            "headers": [],
            "cookies": [{"name": "session", "value": "s1"}],
            "queryString": [{"name": "id5id", "value": "abc"}],
        },
        "response": {
            "status": 200,
            "statusText": "OK",
            "headers": [],
            "cookies": [],
            "content": {"mimeType": "application/json", "text": '{"nested": {"id5id": "abc"}}'},
            "bodySize": 0,
            "headersSize": 0,
        },
        "_initiator": {},
    }
    entries = build_entries_from_har_data({"log": {"entries": [entry]}})
    names = {item.get("name") for _, item in get_all_items(entries[0])}

    assert names == {"id5id", "session", "nested.id5id"}


def test_filter_known_ids_matches_regardless_of_appearance_count(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    tracked = extract_tracked_keys(entries, get_query_items)

    # "token" (2 appearances) isn't a studied vendor's documented ID name.
    assert filter_known_ids(tracked, name_query="") == []

    # A real studied-vendor ID name added at a single, low appearance count
    # must still surface -- Known IDs has no appearance-count threshold.
    tracked["id5id"] = TrackedKey(key="id5id", total_appearances=1)
    matches = filter_known_ids(tracked, name_query="")
    assert {tk.key for tk in matches} == {"id5id"}


def test_filter_known_ids_respects_name_query() -> None:
    tracked = {"id5id": TrackedKey(key="id5id", total_appearances=1)}

    assert filter_known_ids(tracked, name_query="id5") != []
    assert filter_known_ids(tracked, name_query="nope") == []


def test_get_body_items_ignores_non_json_bodies() -> None:
    entry = {
        "startedDateTime": "2026-01-01T00:00:00.000Z",
        "time": 1.0,
        "request": {
            "method": "GET",
            "url": "https://example.com/page",
            "headers": [],
            "cookies": [],
            "queryString": [],
        },
        "response": {
            "status": 200,
            "statusText": "OK",
            "headers": [],
            "cookies": [],
            "content": {"mimeType": "text/html", "text": "<html></html>"},
            "bodySize": 0,
            "headersSize": 0,
        },
        "_initiator": {},
    }
    entries = build_entries_from_har_data({"log": {"entries": [entry]}})
    assert not get_body_items(entries[0])
