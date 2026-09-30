from pathlib import Path

from app.shared.trackers import (
    TrackerInfo,
    classify_domain,
    is_same_site,
    load_trackers,
)

SAMPLE_TABLE = {
    "cbssports.com": TrackerInfo(service="Paramount", category="", description=""),
    "liadm.com": TrackerInfo(
        service="Live Intent",
        category="identity_graph",
        description="identity resolution & cookie-sync",
    ),
    "rp.liadm.com": TrackerInfo(
        service="Live Intent", category="identity_graph", description="Identity resolution"
    ),
}


def test_classify_domain_exact_match() -> None:
    assert classify_domain("cbssports.com", SAMPLE_TABLE) == SAMPLE_TABLE["cbssports.com"]


def test_classify_domain_matches_subdomain_of_a_table_entry() -> None:
    match = classify_domain("video-api-ipv4.cbssports.com", SAMPLE_TABLE)
    assert match == SAMPLE_TABLE["cbssports.com"]


def test_classify_domain_prefers_the_more_specific_entry() -> None:
    # Both "liadm.com" and "rp.liadm.com" are in the table -- a hit on the
    # more specific one should win, not fall through to the generic parent.
    assert classify_domain("rp.liadm.com", SAMPLE_TABLE) == SAMPLE_TABLE["rp.liadm.com"]


def test_classify_domain_does_not_false_positive_on_a_similar_looking_domain() -> None:
    # "evilcbssports.com" is not a subdomain of "cbssports.com" -- there's no
    # dot boundary between "evil" and "cbssports", so this must not match.
    assert classify_domain("evilcbssports.com", SAMPLE_TABLE) is None


def test_classify_domain_returns_none_for_an_unknown_domain() -> None:
    assert classify_domain("totally-unrelated.example.org", SAMPLE_TABLE) is None


def test_is_same_site_exact_match() -> None:
    assert is_same_site("cbssports.com", "cbssports.com") is True


def test_is_same_site_matches_a_subdomain_of_the_primary() -> None:
    assert is_same_site("video-api-ipv4.cbssports.com", "cbssports.com") is True


def test_is_same_site_rejects_an_unrelated_domain() -> None:
    assert is_same_site("id5-sync.com", "cbssports.com") is False


def test_is_same_site_does_not_false_positive_on_a_similar_looking_domain() -> None:
    assert is_same_site("evilcbssports.com", "cbssports.com") is False


def test_is_same_site_is_false_when_no_primary_domain_is_known() -> None:
    assert is_same_site("anything.com", "") is False


def test_is_same_site_ignores_a_port_on_the_entry_domain() -> None:
    # ParsedEntry.domain is urlparse(url).netloc, which keeps a non-default
    # port -- "example.com:8443" is still first-party against "example.com".
    assert is_same_site("example.com:8443", "example.com") is True


def test_is_same_site_ignores_a_port_on_the_primary_domain() -> None:
    assert is_same_site("example.com", "example.com:8443") is True


def test_classify_domain_ignores_a_port_on_the_entry_domain() -> None:
    assert classify_domain("cbssports.com:8443", SAMPLE_TABLE) == SAMPLE_TABLE["cbssports.com"]


def test_classify_domain_is_case_insensitive() -> None:
    assert classify_domain("CBSSports.com", SAMPLE_TABLE) == SAMPLE_TABLE["cbssports.com"]


def test_load_trackers_returns_empty_dict_for_missing_file() -> None:
    assert load_trackers(Path("/does/not/exist.csv")) == {}


def test_load_trackers_parses_a_real_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "trackers.csv"
    csv_path.write_text(
        "domain,service,category,description\n"
        "example.com,Example Inc,advertising,\n"
        'quoted.com,"Has, Comma",,"A description, with a comma"\n',
        encoding="utf-8",
    )
    table = load_trackers(csv_path)

    assert table["example.com"] == TrackerInfo(
        service="Example Inc", category="advertising", description=""
    )
    assert table["quoted.com"] == TrackerInfo(
        service="Has, Comma", category="", description="A description, with a comma"
    )


def test_real_generated_trackers_csv_loads_and_classifies_known_domains() -> None:
    """Smoke test against the actual committed backend/app/data/trackers.csv
    -- catches the generated file itself being broken/empty, which the
    synthetic-fixture tests above can't."""
    from app.shared.trackers import DEFAULT_TRACKERS_CSV

    table = load_trackers(DEFAULT_TRACKERS_CSV)
    assert len(table) > 1000  # tens of thousands expected; generous floor

    liadm = classify_domain("rp.liadm.com", table)
    assert liadm is not None
    assert liadm.service == "Live Intent"


def test_classify_domain_default_table_path_is_cached() -> None:
    """classify_domain() with no explicit table goes through the real,
    import-time-loaded data and an lru_cache -- confirm it's actually being
    hit, not just that the answer happens to be right."""
    from app.shared.trackers import (
        _classify_default,  # pylint: disable=protected-access
    )

    first = classify_domain("rp.liadm.com")
    second = classify_domain("rp.liadm.com")
    assert first == second
    assert first is not None
    assert first.service == "Live Intent"
    assert _classify_default.cache_info().hits >= 1
