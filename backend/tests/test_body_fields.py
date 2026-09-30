from app.core.models import build_entries_from_har_data
from app.features.body_fields import (
    aggregate_body_field_records,
    collect_body_field_records,
)


def _entry_with_body(res_body: str) -> dict:
    return {
        "startedDateTime": "2026-01-01T00:00:00.000Z",
        "time": 1.0,
        "request": {"method": "GET", "url": "https://example.com/id", "headers": [], "cookies": [], "queryString": []},
        "response": {
            "status": 200,
            "statusText": "OK",
            "headers": [],
            "cookies": [],
            "content": {"mimeType": "application/json", "text": res_body},
            "bodySize": 0,
            "headersSize": 0,
        },
        "_initiator": {},
    }


def test_collect_body_field_records_flattens_nested_json() -> None:
    entries = build_entries_from_har_data(
        {"log": {"entries": [_entry_with_body('{"fms_params": {"fms_uid2": "A4-token"}}')]}}
    )
    records = collect_body_field_records(entries)

    assert len(records) == 1
    assert records[0] == {"Name": "fms_params.fms_uid2", "Value": "A4-token", "Scope": "Response Body", "Host": "example.com"}


def test_collect_body_field_records_ignores_non_json_bodies() -> None:
    entries = build_entries_from_har_data({"log": {"entries": [_entry_with_body("<html></html>")]}})
    assert collect_body_field_records(entries) == []


def test_aggregate_body_field_records_groups_by_path() -> None:
    records = [
        {"Name": "fms_uid2", "Value": "A4-token", "Scope": "Response Body", "Host": "a.com"},
        {"Name": "fms_uid2", "Value": "A4-token", "Scope": "POST Data", "Host": "b.com"},
    ]
    aggregated = aggregate_body_field_records(records)

    assert len(aggregated) == 1
    row = aggregated[0]
    assert row["Name"] == "fms_uid2"
    assert row["Value"] == "A4-token"
    assert row["Scope"] == "POST Data, Response Body"
    assert row["Occurrences"] == 2
    assert row["Hosts"] == "a.com, b.com"
