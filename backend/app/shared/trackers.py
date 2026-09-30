"""Domain -> known-tracker lookup, built from backend/app/data/trackers.csv
(see backend/scripts/sync_tracker_data.py for how that file is generated).

Matching is suffix-based, most-specific first, with no TLD/public-suffix-list
logic needed: a HAR hostname like "video-api-ipv4.cbssports.com" won't
literally equal a table entry like "cbssports.com", so each candidate from
the full hostname down to shorter suffixes is checked against the table's
literal string keys -- whichever one hits first (the most specific) wins.
This also correctly prefers a documented subdomain's own, more precise entry
(e.g. "rp.liadm.com") over its parent domain's more generic one
("liadm.com") when both are present in the table.
"""

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.shared.data_files import APP_DATA_DIR

DEFAULT_TRACKERS_CSV = APP_DATA_DIR / "trackers.csv"

TrackerTable = dict[str, "TrackerInfo"]


@dataclass(frozen=True, slots=True)
class TrackerInfo:
    """What backend/app/data/trackers.csv knows about one domain."""

    service: str
    category: str
    description: str


def load_trackers(csv_path: Path = DEFAULT_TRACKERS_CSV) -> TrackerTable:
    """domain -> TrackerInfo, lowercased. Missing file (e.g. a from-scratch
    checkout before the sync script has ever run) is not an error -- it just
    means no domain gets classified, same as any other reference data this
    app treats as optional."""
    if not csv_path.is_file():
        return {}
    table: TrackerTable = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            domain = (row.get("domain") or "").strip().lower()
            if domain:
                table[domain] = TrackerInfo(
                    service=(row.get("service") or "").strip(),
                    category=(row.get("category") or "").strip(),
                    description=(row.get("description") or "").strip(),
                )
    return table


# Loaded once at import -- static reference data, not per-upload state.
_TRACKERS: TrackerTable = load_trackers()


@lru_cache(maxsize=None)
def _candidate_suffixes(domain: str) -> tuple[str, ...]:
    """The domain itself, then each shorter parent suffix, most specific
    first -- e.g. "a.b.c.com" -> "a.b.c.com", "b.c.com", "c.com". Stops
    before a single bare label (e.g. "com" alone): no real entry in the
    table is ever a single label, so checking it would only ever waste a
    lookup, never match.

    Cached on ``domain`` alone: both classify_domain (via _lookup) and
    is_same_site call this for the very same domain within one
    build_entry_summary call, and the same handful of hostnames repeat
    across thousands of entries in a capture -- same bounded-domain-space
    assumption _classify_default's own cache already relies on.

    Not app.features.overview.get_base_domain -- that collapses a domain
    down to exactly one root for aggregation (with its own co.uk/gov.uk
    handling); this needs every candidate suffix, most-specific first, to
    look each one up against a table that can contain entries at any depth
    (e.g. both "liadm.com" and "rp.liadm.com").

    A ParsedEntry.domain is urlparse(url).netloc (app.core.models.get_domain),
    which keeps a non-default port (e.g. "example.com:8443") -- stripped
    here the same way app.features.metadata already does for its own host
    extraction, otherwise a ported domain would never match even itself."""
    host = domain.strip(".").lower().split(":")[0]
    labels = host.split(".")
    return tuple(".".join(labels[i:]) for i in range(len(labels) - 1))


def _lookup(domain: str, trackers: TrackerTable) -> TrackerInfo | None:
    for candidate in _candidate_suffixes(domain):
        match = trackers.get(candidate)
        if match is not None:
            return match
    return None


@lru_cache(maxsize=None)
def _classify_default(domain: str) -> TrackerInfo | None:
    """Cached wrapper around the real, import-time-loaded table. A capture
    routinely has thousands of entries reusing a small set of hostnames (the
    same CDN/analytics/ad domain hit repeatedly), so this turns every repeat
    hostname into one cache hit instead of re-walking the suffix chain. Kept
    separate from classify_domain's injectable-``table`` path so tests (which
    always pass an explicit table) never interact with -- or need to worry
    about -- this cache at all."""
    return _lookup(domain, _TRACKERS)


def classify_domain(domain: str, table: TrackerTable | None = None) -> TrackerInfo | None:
    """The most specific known-tracker match for this domain, or None if it
    isn't in the table at all. ``table`` is injectable for tests; omit it to
    use the real data loaded at import (cached -- see _classify_default)."""
    if table is not None:
        return _lookup(domain, table)
    return _classify_default(domain)


def is_same_site(domain: str, primary_domain: str) -> bool:
    """True if ``domain`` is ``primary_domain`` itself or a subdomain of it
    -- the same suffix rule classify_domain checks a whole table with,
    applied instead against a single reference domain (the capture's own
    tagged/detected site) to answer "is this entry first-party?"."""
    if not primary_domain:
        return False
    # primary_domain can itself carry a port (it may come straight from a
    # ParsedEntry.domain via derive_metadata_from_entries' fallback), so it
    # needs the same port-stripping _candidate_suffixes applies to `domain`.
    primary = primary_domain.strip().lower().split(":")[0]
    return primary in _candidate_suffixes(domain)
