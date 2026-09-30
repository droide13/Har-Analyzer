from datetime import datetime

import pytest

from app.core.models import build_entries_from_har_data
from app.shared.naming import (
    derive_metadata_from_entries,
    get_attrs_from_har_name,
    get_har_filename,
    resolve_primary_domain,
)


def test_get_har_filename_and_parse_round_trip() -> None:
    now = datetime(2026, 7, 17, 17, 0)
    filename = get_har_filename(
        domain="boredpanda.com",
        platform="web",
        interact="login",
        cookies="accept",
        visit="first",
        extra="extra-context",
        now=now,
    )
    assert filename == (
        "boredpanda.com-platform-WEB-interact-LOG-cookies-ACC-visit-FIR-extra-EXT-26-07-17-17.har"
    )

    attrs = get_attrs_from_har_name(filename)
    assert attrs is not None
    assert attrs["domain"] == "boredpanda.com"
    assert attrs["platform"] == "Web"
    assert attrs["interaction"] == "Login"
    assert attrs["cookies"] == "Accept"
    assert attrs["extra"] == "EXT"
    assert attrs["timestamp"] == "2026-07-17 @ 17:00"


def test_get_har_filename_rejects_invalid_codes() -> None:
    with pytest.raises(ValueError):
        get_har_filename(
            domain="example.com", platform="web", interact="teleport", cookies="accept"
        )
    with pytest.raises(ValueError):
        get_har_filename(domain="", platform="web", interact="login", cookies="accept")
    with pytest.raises(ValueError):
        get_har_filename(
            domain="example.com", platform="desktop", interact="login", cookies="accept"
        )


def test_get_attrs_from_har_name_rejects_non_matching_filename() -> None:
    assert get_attrs_from_har_name("not-a-standardized-name.har") is None


def test_derive_metadata_from_entries_picks_most_common_domain(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    derived = derive_metadata_from_entries(entries)

    # example.com appears on 4 of the 5 entries, cdn.example.com on 1.
    assert derived.domain == "example.com"
    assert derived.other_domains == ["cdn.example.com"]
    assert derived.entry_count == 5
    assert derived.captured_at is not None


def test_derive_metadata_from_entries_rejects_empty_list() -> None:
    with pytest.raises(ValueError):
        derive_metadata_from_entries([])


def test_resolve_primary_domain_prefers_embedded_analysis(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    filename = (
        "fromfilename.com-platform-WEB-interact-LOA-cookies-ACC-visit-FIR-extra-000-26-01-01-10.har"
    )
    har_data = {
        **sample_har_dict,
        "log": {**sample_har_dict["log"], "_analysis": {"domain": "fromembedded.com"}},
    }

    # Even though the filename tags "fromfilename.com", a previously
    # embedded log._analysis.domain (set by the Metadata tab's generate
    # flow) wins -- it's the one value a user can actually correct.
    assert resolve_primary_domain(filename, har_data, entries) == "fromembedded.com"


def test_resolve_primary_domain_prefers_the_standardized_filename(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    filename = (
        "fromfilename.com-platform-WEB-interact-LOA-cookies-ACC-visit-FIR-extra-000-26-01-01-10.har"
    )

    assert resolve_primary_domain(filename, sample_har_dict, entries) == "fromfilename.com"


def test_resolve_primary_domain_falls_back_to_derived_domain(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)

    assert (
        resolve_primary_domain("not-a-standardized-name.har", sample_har_dict, entries)
        == "example.com"
    )


def test_resolve_primary_domain_falls_back_to_filename_when_nothing_else_works() -> None:
    assert resolve_primary_domain("empty.har", {}, []) == "empty.har"
