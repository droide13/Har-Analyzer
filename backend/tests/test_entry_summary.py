from app.core.models import build_entries_from_har_data
from app.shared.entry_summary import build_entry_summary


def test_build_entry_summary_covers_base_fields(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    summary = build_entry_summary(entries[0])

    assert summary.index == 0
    assert summary.method == "GET"
    assert summary.domain == "example.com"
    assert summary.req_cookie_count == 1
    assert summary.res_cookie_count == 1
    # Filter/highlight fields are the caller's responsibility to set.
    assert summary.filter_summary is None
    assert summary.highlighted is False
    assert summary.highlight_summary is None
