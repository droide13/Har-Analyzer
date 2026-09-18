"""Builds the Network-Log-shaped EntrySummary from a ParsedEntry.

Pulled out because two routers need the exact same row shape: Network Log's
own listing (har.py) and Dissemination's matching-entries list
(dissemination.py), which reuses EntrySummary so it can share the frontend's
row/detail-panel components instead of inventing a parallel shape.
"""

from app.core.models import ParsedEntry
from app.schemas import EntrySummary


def build_entry_summary(entry: ParsedEntry) -> EntrySummary:
    """The base EntrySummary fields; callers set filter/highlight fields themselves."""
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
    )
