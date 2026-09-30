from app.schemas import BadgeFieldMatch, EntryBadge, TrackerSummary


def test_entry_badge_keeps_its_matches_field() -> None:
    # Regression: TrackerSummary was once accidentally inserted inside
    # EntryBadge's own class body, which silently moved `matches` onto
    # TrackerSummary instead -- Pydantic drops unknown kwargs rather than
    # erroring, so every badge in the API response lost its `matches` list
    # without a single test failing.
    badge = EntryBadge(
        label="Filtered via: URL",
        tone="neutral",
        matches=[BadgeFieldMatch(attr="url", label="URL", text="example.com")],
    )
    assert badge.model_dump()["matches"] == [{"attr": "url", "label": "URL", "text": "example.com"}]


def test_tracker_summary_has_no_matches_field() -> None:
    tracker = TrackerSummary(service="ID5", category="identity_graph", description="")
    assert "matches" not in tracker.model_dump()
