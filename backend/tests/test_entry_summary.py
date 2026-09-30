from app.core.models import build_entries_from_har_data
from app.shared.entry_summary import build_entry_summary


def test_build_entry_summary_covers_base_fields(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    summary = build_entry_summary(entries[0], "")

    assert summary.index == 0
    assert summary.method == "GET"
    assert summary.domain == "example.com"
    assert summary.req_cookie_count == 1
    assert summary.res_cookie_count == 1
    # Filter/highlight fields are the caller's responsibility to set.
    assert summary.highlighted is False
    assert summary.badges == []


def test_build_entry_summary_is_not_first_party_when_primary_domain_is_empty(
    sample_har_dict: dict,
) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    summary = build_entry_summary(entries[0], "")

    assert summary.is_first_party is False


def test_build_entry_summary_is_first_party_when_domain_matches_primary(
    sample_har_dict: dict,
) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    summary = build_entry_summary(entries[0], "example.com")

    assert summary.is_first_party is True
    assert summary.tracker is None


def test_build_entry_summary_classifies_a_known_tracker_domain() -> None:
    entry_dict = {
        "startedDateTime": "2026-01-01T00:00:00.000Z",
        "time": 1.0,
        "request": {
            "method": "GET",
            "url": "https://id5-sync.com/id5",
            "headers": [],
            "cookies": [],
            "queryString": [],
        },
        "response": {
            "status": 200,
            "statusText": "OK",
            "headers": [],
            "cookies": [],
            "content": {"mimeType": "text/plain", "text": ""},
            "bodySize": 0,
            "headersSize": 0,
        },
    }
    entries = build_entries_from_har_data({"log": {"entries": [entry_dict]}})
    summary = build_entry_summary(entries[0], "example.com")

    assert summary.is_first_party is False
    assert summary.tracker is not None
    assert summary.tracker.service == "ID5"
    assert summary.tracker.category == "identity_graph"
