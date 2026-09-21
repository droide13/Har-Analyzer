from app.core.models import build_entries_from_har_data
from app.features.overview import (
    build_domain_map,
    calculate_overview_summary,
    get_base_domain,
    get_first_party_domain,
    get_method_counts,
    get_status_counts,
)


def test_get_base_domain() -> None:
    assert get_base_domain("api.github.com") == "github.com"
    assert get_base_domain("github.com") == "github.com"
    assert get_base_domain("example.co.uk") == "example.co.uk"
    assert get_base_domain("unknown") == "unknown"
    assert get_base_domain("") == "unknown"


def test_calculate_overview_summary(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    summary = calculate_overview_summary(entries)
    assert summary["total_requests"] == 5
    assert summary["unique_domains"] == 2  # example.com, cdn.example.com
    assert summary["avg_latency_ms"] > 0


def test_get_method_and_status_counts(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    methods = get_method_counts(entries)
    statuses = get_status_counts(entries)
    assert methods == {"GET": 4, "POST": 1}
    assert statuses["200"] == 3
    assert statuses["302"] == 1
    assert statuses["404"] == 1


def test_build_domain_map_aggregates_by_root_and_subdomain(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    domain_map = build_domain_map(entries)

    # cdn.example.com's root is also "example.com", so both subdomains roll
    # up under the one root key, with the root tallying all 5 entries.
    assert list(domain_map.keys()) == ["example.com"]
    assert domain_map["example.com"]["requests"] == 5
    assert domain_map["example.com"]["subdomains"]["example.com"]["requests"] == 4
    assert domain_map["example.com"]["subdomains"]["cdn.example.com"]["requests"] == 1


def test_get_first_party_domain_prefers_filename(sample_har_dict: dict) -> None:
    entries = build_entries_from_har_data(sample_har_dict)
    standardized = (
        "other.org-platform-WEB-interact-LOA-cookies-ACC-visit-FIR-extra-000-26-01-01-10.har"
    )
    assert get_first_party_domain(entries, standardized) == "other.org"
    # Falls back to traffic when the filename doesn't parse.
    assert get_first_party_domain(entries, "not-standardized.har") == "example.com"
