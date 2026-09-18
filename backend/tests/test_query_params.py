from app.core.models import build_entries_from_har_data
from app.features.query_params import aggregate_query_param_records, collect_query_param_records


def test_collect_query_param_records(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    records = collect_query_param_records(entries)

    # entries 0 and 3 both carry token=abc123; nothing else has query params.
    assert len(records) == 2
    assert all(r["Name"] == "token" and r["Value"] == "abc123" for r in records)


def test_aggregate_query_param_records_same_value_every_time(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    records = collect_query_param_records(entries)
    aggregated = aggregate_query_param_records(records)

    assert len(aggregated) == 1
    row = aggregated[0]
    assert row["Name"] == "token"
    assert row["Value"] == "abc123"
    assert row["Method"] == "Always GET"
    assert row["Occurrences"] == 2
