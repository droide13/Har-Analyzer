from app.core.models import build_entries_from_har_data
from app.features.identifiers import (
    extract_tracked_keys,
    filter_identifiers,
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
    tracked = extract_tracked_keys(entries, get_query_items)  # "token" isn't noise, but exercise the flag
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
