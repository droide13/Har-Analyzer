from app.core.models import build_entries_from_har_data
from app.features.dissemination import (
    aggregate_by_domain,
    build_initiator_chain,
    collect_occurrences,
    distinct_values,
    find_dissemination,
    key_options,
    value_timeline,
)
from app.shared.search import dissemination_badge_labels
from tests.conftest import ENCODED_ONLY_VALUE


def _entry(url: str, when: str, initiator: dict | None = None) -> dict:
    return {
        "startedDateTime": when,
        "time": 1.0,
        "request": {"method": "GET", "url": url, "headers": [], "cookies": [], "queryString": []},
        "response": {
            "status": 200,
            "statusText": "OK",
            "headers": [],
            "cookies": [],
            "content": {"mimeType": "text/plain", "text": ""},
            "bodySize": 0,
            "headersSize": 0,
        },
        "_initiator": initiator or {},
    }


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


def test_build_initiator_chain_walks_back_through_script_initiated_hops() -> None:
    # doc (parser-initiated a.js) -> a.js (script-initiated b.js, via the
    # call stack, matching real Chrome HAR exports for type="script") ->
    # b.js -> made the value-carrying request. Mirrors the real bug: a
    # "script" initiator's URL only lives in stack.callFrames[0].url, not
    # the top-level initiator.url.
    har = {
        "log": {
            "entries": [
                _entry("https://example.com/", "2026-01-01T10:00:00.000Z"),
                _entry(
                    "https://cdn.example.com/a.js",
                    "2026-01-01T10:00:01.000Z",
                    initiator={"type": "parser", "url": "https://example.com/"},
                ),
                _entry(
                    "https://cdn.example.com/b.js",
                    "2026-01-01T10:00:02.000Z",
                    initiator={
                        "type": "script",
                        "stack": {"callFrames": [{"url": "https://cdn.example.com/a.js", "lineNumber": 1}]},
                    },
                ),
                _entry(
                    "https://api.example.com/collect?id=xyz",
                    "2026-01-01T10:00:03.000Z",
                    initiator={
                        "type": "script",
                        "stack": {"callFrames": [{"url": "https://cdn.example.com/b.js", "lineNumber": 2}]},
                    },
                ),
            ]
        }
    }
    entries = build_entries_from_har_data(har)

    chain = build_initiator_chain(entries, entries[3])

    assert [hop.url for hop in chain] == [
        "https://example.com/",
        "https://cdn.example.com/a.js",
        "https://cdn.example.com/b.js",
    ]
    assert all(hop.found for hop in chain)
    assert [hop.entry.index for hop in chain] == [0, 1, 2]  # type: ignore[union-attr]


def test_build_initiator_chain_empty_when_no_initiator() -> None:
    har = {"log": {"entries": [_entry("https://example.com/", "2026-01-01T10:00:00.000Z")]}}
    entries = build_entries_from_har_data(har)

    assert build_initiator_chain(entries, entries[0]) == []


def test_build_initiator_chain_stops_at_uncaptured_url() -> None:
    har = {
        "log": {
            "entries": [
                _entry(
                    "https://api.example.com/collect?id=xyz",
                    "2026-01-01T10:00:00.000Z",
                    initiator={"type": "script", "url": "https://cdn.example.com/not-captured.js"},
                ),
            ]
        }
    }
    entries = build_entries_from_har_data(har)

    chain = build_initiator_chain(entries, entries[0])

    assert len(chain) == 1
    assert chain[0].found is False
    assert chain[0].url == "https://cdn.example.com/not-captured.js"
    assert chain[0].entry is None
