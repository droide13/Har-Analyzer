"""Extraction logic for tracing a key or value across all HAR entries.

Two search modes:
  - By key: find every occurrence of a given param/cookie name, in request
    order, and flag when its value changes between consecutive occurrences.
  - By value: find every place a given substring shows up (query params,
    cookies, optionally headers/body), regardless of key name -- useful for
    tracking dissemination of a specific token across domains.
"""

from dataclasses import dataclass
from typing import Any

from core.models import ParsedEntry

BODY_PREVIEW_LENGTH = 120


@dataclass(slots=True)
class Occurrence:
    """A single sighting of a key/value pair in one HAR entry."""

    entry_index: int
    method: str
    host: str
    url: str
    source: str
    key: str
    value: str
    changed_from_previous: bool = False


def collect_known_keys(entries: list[ParsedEntry]) -> list[str]:
    """Union of every query param name and cookie name seen, for the key picker."""
    keys: set[str] = set()
    for e in entries:
        for qp in e.query_params:
            keys.add(str(qp.get("name", "")))
        for c in e.req_cookies + e.res_cookies:
            keys.add(str(c.get("name", "")))
    keys.discard("")
    return sorted(keys)


def _mark_changes(occurrences: list[Occurrence]) -> None:
    """Flag each occurrence whose value differs from the prior occurrence of the same key."""
    previous_value: str | None = None
    for occ in occurrences:
        occ.changed_from_previous = previous_value is not None and occ.value != previous_value
        previous_value = occ.value


def _occurrences_from_cookies(
    e: ParsedEntry, cookies: list[dict[str, Any]], key: str, source: str
) -> list[Occurrence]:
    """Build Occurrence entries for cookies on one HAR entry matching `key`."""
    return [
        Occurrence(e.index, e.method, e.domain, e.url, source, key, str(c.get("value", "")))
        for c in cookies
        if str(c.get("name", "")) == key
    ]


def find_key_occurrences(entries: list[ParsedEntry], key: str) -> list[Occurrence]:
    """All sightings of a specific param/cookie name, in request order, with change flags."""
    occurrences: list[Occurrence] = []

    for e in entries:
        for qp in e.query_params:
            if str(qp.get("name", "")) == key:
                occurrences.append(
                    Occurrence(
                        e.index,
                        e.method,
                        e.domain,
                        e.url,
                        "Query Param",
                        key,
                        str(qp.get("value", "")),
                    )
                )
        occurrences.extend(_occurrences_from_cookies(e, e.req_cookies, key, "Request Cookie"))
        occurrences.extend(_occurrences_from_cookies(e, e.res_cookies, key, "Response Cookie"))

    occurrences.sort(key=lambda o: o.entry_index)
    _mark_changes(occurrences)
    return occurrences


def _truncate(text: str) -> str:
    """Shorten long body text for display while keeping the match visible."""
    if len(text) <= BODY_PREVIEW_LENGTH:
        return text
    return text[:BODY_PREVIEW_LENGTH] + "..."


def _matching_pairs(items: list[dict[str, Any]], needle: str) -> list[tuple[str, str]]:
    """Return (name, value) pairs from headers/params/cookies whose value contains needle."""
    pairs: list[tuple[str, str]] = []
    for item in items:
        value = str(item.get("value", ""))
        if needle in value.lower():
            pairs.append((str(item.get("name", "")), value))
    return pairs


def _entry_value_matches(e: ParsedEntry, needle: str, include_headers: bool) -> list[Occurrence]:
    """All param/cookie/header matches on one entry for a given search substring."""
    matches: list[Occurrence] = []

    sources: list[tuple[list[dict[str, Any]], str]] = [
        (e.query_params, "Query Param"),
        (e.req_cookies, "Request Cookie"),
        (e.res_cookies, "Response Cookie"),
    ]
    if include_headers:
        sources.append((e.req_headers, "Request Header"))
        sources.append((e.res_headers, "Response Header"))

    for items, source in sources:
        for name, value in _matching_pairs(items, needle):
            matches.append(Occurrence(e.index, e.method, e.domain, e.url, source, name, value))

    return matches


def _entry_body_matches(e: ParsedEntry, needle: str) -> list[Occurrence]:
    """Request/response body matches on one entry for a given search substring."""
    matches: list[Occurrence] = []
    if needle in e.req_body.lower():
        matches.append(
            Occurrence(
                e.index, e.method, e.domain, e.url, "Request Body", "(body)", _truncate(e.req_body)
            )
        )
    if needle in e.res_body.lower():
        matches.append(
            Occurrence(
                e.index, e.method, e.domain, e.url, "Response Body", "(body)", _truncate(e.res_body)
            )
        )
    return matches


def find_value_occurrences(
    entries: list[ParsedEntry],
    search_value: str,
    include_headers: bool,
    include_body: bool,
) -> list[Occurrence]:
    """All sightings of a substring, across params/cookies and optionally headers/body."""
    needle = search_value.lower()
    matches: list[Occurrence] = []

    for e in entries:
        matches.extend(_entry_value_matches(e, needle, include_headers))
        if include_body:
            matches.extend(_entry_body_matches(e, needle))

    matches.sort(key=lambda o: o.entry_index)
    return matches


def summarize(occurrences: list[Occurrence]) -> dict[str, Any]:
    """Aggregate stats for the metrics row: spread, hosts touched, sources involved."""
    if not occurrences:
        return {
            "total": 0,
            "distinct_hosts": 0,
            "hosts": "",
            "first_index": None,
            "last_index": None,
        }

    hosts = sorted({o.host for o in occurrences})
    return {
        "total": len(occurrences),
        "distinct_hosts": len(hosts),
        "hosts": ", ".join(hosts),
        "first_index": occurrences[0].entry_index,
        "last_index": occurrences[-1].entry_index,
    }
