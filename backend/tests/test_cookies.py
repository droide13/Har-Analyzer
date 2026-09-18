from app.core.models import build_entries_from_har_data
from app.features.cookies import aggregate_cookie_records, collect_cookie_records


def test_collect_cookie_records_covers_both_sides(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    records = collect_cookie_records(entries)

    # "session" is sent as a request cookie on entries 0 and 3, and set as a
    # response cookie on entry 1 (a different value) -- 3 sightings total.
    names = [r["Name"] for r in records]
    assert names.count("session") == 3
    assert names.count("tracking_id") == 1
    assert {r["Scope"] for r in records} == {"Request Cookie", "Response Cookie"}


def test_aggregate_cookie_records_flags_mixed_values(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    records = collect_cookie_records(entries)
    aggregated = {row["Name"]: row for row in aggregate_cookie_records(records)}

    # "session" appears as sess-1 (request, entry 0 & 3) and sess-2 (response, entry 1).
    assert aggregated["session"]["Value"] == "Multiple values (2)"
    assert aggregated["session"]["Occurrences"] == 3
    assert aggregated["session"]["First Seen As"] == "Request Cookie"

    # "tracking_id" only ever appears with one value, on the response side.
    assert aggregated["tracking_id"]["Value"] == "trk-999"
    assert aggregated["tracking_id"]["Secure"] == "Never"
