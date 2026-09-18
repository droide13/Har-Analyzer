from datetime import datetime

import pytest

from app.core.models import build_entries_from_har_data
from app.features.metadata import (
    StandardizeInputs,
    analysis_table_rows,
    build_standardized_result,
    collect_domain_options,
    extract_entry_domain,
    is_custom_domain_choice,
)


def test_build_standardized_result_builds_filename_and_analysis() -> None:
    inputs = StandardizeInputs(
        domain="Example.com",
        interact="login",
        cookies="accept",
        visit="first",
        extra="extra context",
        captured_at=datetime(2026, 7, 17, 17, 0),
        description="  a test capture  ",
        email_used="test@example.com",
        notes="",
    )
    filename, analysis = build_standardized_result(inputs)

    assert filename == "Example.com-interact-LOG-cookies-ACC-visit-FIR-extra-EXT-26-07-17-17.har"
    assert analysis.domain == "Example.com"
    assert analysis.interact == "login"
    assert analysis.extra == "EXT"
    assert analysis.description == "a test capture"
    assert analysis.standardized_filename == filename


def test_build_standardized_result_rejects_invalid_codes() -> None:
    inputs = StandardizeInputs(
        domain="example.com",
        interact="not-a-real-interaction",
        cookies="accept",
        visit="first",
        extra="",
        captured_at=datetime.now(),
    )
    with pytest.raises(ValueError):
        build_standardized_result(inputs)


def test_extract_entry_domain_prefers_domain_field() -> None:
    class FakeEntry:
        domain = "example.com"
        url = "https://other.example/path"

    assert extract_entry_domain(FakeEntry()) == "example.com"


def test_extract_entry_domain_falls_back_to_url() -> None:
    class FakeEntry:
        domain = ""
        url = "https://sub.example.com:8443/path"

    assert extract_entry_domain(FakeEntry()) == "sub.example.com"


def test_collect_domain_options_orders_and_sentinels(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    options, first_domain = collect_domain_options(
        entries, "example.com", frozenset({"cdn.example.com"})
    )

    assert first_domain == "example.com"  # first request's domain
    assert options[0] == "example.com"
    assert options[-1] == "Custom domain..."
    assert "cdn.example.com" in options
    assert is_custom_domain_choice(options[-1])
    assert not is_custom_domain_choice("example.com")


def test_analysis_table_rows_humanizes_field_names() -> None:
    from app.core.models import HarAnalysis

    analysis = HarAnalysis(
        domain="example.com",
        interact="login",
        cookies="accept",
        visit="first",
        extra="000",
        captured_at="2026-01-01T00:00:00",
        standardized_filename="x.har",
    )
    rows = {row["Field"]: row["Value"] for row in analysis_table_rows(analysis)}
    assert rows["Standardized Filename"] == "x.har"
    assert rows["Domain"] == "example.com"
