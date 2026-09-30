"""Builds the Network-Log-shaped EntrySummary from a ParsedEntry.

Pulled out because two routers need the exact same row shape: Network Log's
own listing (har.py) and Dissemination's matching-entries list
(dissemination.py), which reuses EntrySummary so it can share the frontend's
row/detail-panel components instead of inventing a parallel shape.
"""

from app.core.models import ParsedEntry
from app.schemas import EntrySummary, TrackerSummary
from app.shared.trackers import classify_domain, is_same_site


def build_entry_summary(entry: ParsedEntry, primary_domain: str) -> EntrySummary:
    """The base EntrySummary fields; callers set filter/highlight fields
    themselves.

    ``primary_domain`` (the capture's own tagged/detected site -- see
    app.shared.naming.resolve_primary_domain) drives the domain
    classification: first-party wins outright over a tracker-table match
    (a site's own analytics running on its own domain isn't "a tracker" in
    the sense this badge means), otherwise a known-tracker match if any.
    Every real caller has this handy (it's resolved once per request), so
    it's required rather than defaulted -- a missing value should be a
    caller bug, not a silent "everything is third-party" classification.
    """
    is_first_party = is_same_site(entry.domain, primary_domain)
    tracker_info = None if is_first_party else classify_domain(entry.domain)
    tracker = (
        TrackerSummary(
            service=tracker_info.service,
            category=tracker_info.category,
            description=tracker_info.description,
        )
        if tracker_info
        else None
    )

    return EntrySummary(
        index=entry.index,
        started_date_time=entry.started_date_time,
        method=entry.method,
        url=entry.url,
        domain=entry.domain,
        status=entry.status,
        status_text=entry.status_text,
        mime=entry.mime,
        time_ms=entry.time_ms,
        body_size=entry.body_size,
        req_cookie_count=len(entry.req_cookies),
        res_cookie_count=len(entry.res_cookies),
        is_first_party=is_first_party,
        tracker=tracker,
    )
