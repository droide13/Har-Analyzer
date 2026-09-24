from app.core.models import build_entries_from_har_data
from app.shared.search import ENCODING_OPTIONS, entry_matches, reason_summary_line
from tests.conftest import ENCODED_ONLY_VALUE


def test_plain_term_matches_url(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    result = entry_matches(entries[0], "example.com", "any", set())
    assert result.matched


def test_field_prefixed_status_wildcard(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    matches = [e.index for e in entries if entry_matches(e, "status:4xx", "any", set()).matched]
    assert matches == [3]


def test_negation_excludes_matches(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    matches = [e.index for e in entries if entry_matches(e, "-status:200", "any", set()).matched]
    # Entries 1 (302) and 3 (404) aren't 200s; entries 0 and 2 are.
    assert matches == [1, 3]


def test_method_filter(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    matches = [e.index for e in entries if entry_matches(e, "", "any", {"POST"}).matched]
    assert matches == [1]


def test_cookie_field_prefix_matches_request_cookie(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    result = entry_matches(entries[0], "cookies:session", "any", set())
    assert result.matched
    assert any(r.attr == "cookies_text" for r in result.reasons)


def test_encoded_value_is_matched_when_encoding_enabled(sample_har_dict: dict) -> None:
    # Entry 4's X-Signature header holds ENCODED_ONLY_VALUE's Base64 form, and
    # nowhere in the entry does the plain value itself appear.
    entries = build_entries_from_har_data(sample_har_dict)
    signed_entry = entries[4]

    with_encoding = entry_matches(signed_entry, ENCODED_ONLY_VALUE, "any", set(), {"Base64"})
    assert with_encoding.matched
    assert any(r.encoding == "Base64" for r in with_encoding.reasons)

    without_encoding = entry_matches(signed_entry, ENCODED_ONLY_VALUE, "any", set(), set())
    assert not without_encoding.matched


def test_all_encoding_options_are_registered() -> None:
    assert len(ENCODING_OPTIONS) >= 10
    assert "Base64" in ENCODING_OPTIONS
    assert "SHA256" in ENCODING_OPTIONS


def test_reason_summary_line_names_field_and_encoding(sample_har_dict: dict) -> None:
    # Network Log's Filtered/Highlighted-via badges: a plain match on the URL
    # plus a Base64-only match on the response headers should read as two
    # "Field (forms)" parts naming both the field and how each one matched.
    entries = build_entries_from_har_data(sample_har_dict)
    signed_entry = entries[4]

    plain_result = entry_matches(signed_entry, "signed", "any", set())
    assert reason_summary_line(plain_result.reasons) == "URL (plain)"

    encoded_result = entry_matches(signed_entry, ENCODED_ONLY_VALUE, "any", set(), {"Base64"})
    assert reason_summary_line(encoded_result.reasons) == "Response Headers (Base64)"
