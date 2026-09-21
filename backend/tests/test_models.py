from app.core.models import (
    HarAnalysis,
    build_entries_from_har_data,
    embed_analysis,
    format_bytes,
    get_domain,
    get_embedded_analysis,
    load_parsed_entries,
    load_raw_har,
    serialize_har,
)


def test_build_entries_from_har_data_parses_all_entries(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    assert len(entries) == 5
    assert [e.index for e in entries] == [0, 1, 2, 3, 4]


def test_parsed_entry_fields_match_source(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    first = entries[0]
    assert first.method == "GET"
    assert first.domain == "example.com"
    assert first.status == "200"
    assert first.mime == "application/json"
    assert "token: abc123" in first.query_params_text
    assert "[Req] session: sess-1" in first.cookies_text
    assert "[Res] tracking_id: trk-999" in first.cookies_text


def test_load_parsed_entries_matches_build_from_dict(
    sample_har_bytes: bytes, sample_har_dict: dict
) -> None:
    assert load_parsed_entries(sample_har_bytes) == build_entries_from_har_data(sample_har_dict)


def test_load_raw_har_round_trips(sample_har_bytes: bytes, sample_har_dict: dict) -> None:
    assert load_raw_har(sample_har_bytes) == sample_har_dict


def test_get_domain_handles_bad_url() -> None:
    assert get_domain("https://example.com/x") == "example.com"
    assert get_domain("not a url at all") == "unknown"
    assert get_domain("") == "unknown"


def test_format_bytes() -> None:
    assert format_bytes(0) == "0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(500) == "500.0 B"


def test_embed_and_read_back_analysis(sample_har_dict: dict) -> None:
    analysis = HarAnalysis(
        domain="example.com",
        platform="web",
        interact="load",
        cookies="accept",
        visit="first",
        extra="000",
        captured_at="2026-01-01T10:00:00+00:00",
        standardized_filename=(
            "example.com-platform-WEB-interact-LOA-cookies-ACC-visit-FIR-extra-000-26-01-01-10.har"
        ),
    )
    updated = embed_analysis(sample_har_dict, analysis)

    # Original dict must be untouched (embed_analysis deep-copies).
    assert get_embedded_analysis(sample_har_dict) is None
    assert get_embedded_analysis(updated) == analysis

    round_tripped = load_raw_har(serialize_har(updated))
    assert get_embedded_analysis(round_tripped) == analysis
