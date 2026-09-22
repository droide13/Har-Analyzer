from app.core.models import build_entries_from_har_data
from app.features.dissemination import (
    aggregate_by_domain,
    collect_occurrences,
    distinct_values,
    find_dissemination,
    key_options,
    value_timeline,
)
from app.shared.search import dissemination_badge_labels
from tests.conftest import ENCODED_ONLY_VALUE


def test_collect_occurrences_and_key_options(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    registry = collect_occurrences(entries)

    assert set(registry) == {"token", "session", "tracking_id"}
    # "session" (3 sightings) should rank above "token"/"tracking_id" (2/1).
    assert key_options(registry)[0] == "session"


def test_value_timeline_flags_changes(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    registry = collect_occurrences(entries)
    timeline = value_timeline(registry["session"])

    assert [row["Value"] for row in timeline] == ["sess-1", "sess-2", "sess-1"]
    assert [row["Value changed"] for row in timeline] == [False, True, True]


def test_distinct_values_dedupes_in_first_seen_order(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    registry = collect_occurrences(entries)
    assert distinct_values(registry["session"]) == ["sess-1", "sess-2"]


def test_find_dissemination_finds_value_beyond_its_own_key(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    # "abc123" is the token's own query-param value on entries 0 and 3 --
    # find_dissemination should surface both, in chronological order.
    matches = find_dissemination(entries, ["abc123"], set())
    assert [entry.index for entry, _ in matches] == [0, 3]

    for _entry, reasons in matches:
        assert dissemination_badge_labels(reasons)  # at least one field label


def test_find_dissemination_respects_encodings(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    without_encoding = find_dissemination(entries, [ENCODED_ONLY_VALUE], set())
    with_encoding = find_dissemination(entries, [ENCODED_ONLY_VALUE], {"Base64"})

    assert without_encoding == []
    assert [e.index for e, _ in with_encoding] == [4]


def test_aggregate_by_domain(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    matches = find_dissemination(entries, ["abc123"], set())
    by_domain = aggregate_by_domain(matches)

    assert len(by_domain) == 1
    assert by_domain[0]["Domain"] == "example.com"
    assert by_domain[0]["Entries Hit"] == 2
