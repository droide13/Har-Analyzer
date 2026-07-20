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
from models import ParsedEntry

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


def find_key_occurrences(entries: list[ParsedEntry], key: str) -> list[Occurrence]:
    """All sightings of a specific param/cookie name, in request order, with change flags."""
    occurrences: list[Occurrence] = []

    for e in entries:
        for qp in e.query_params:
            if str(qp.get("name", "")) == key:
                occurrences.append(Occurrence(
                    e.index, e.method, e.domain, e.url, "Query Param", key, str(qp.get("value", ""))
                ))
        for c in e.req_cookies:
            if str(c.get("name", "")) == key:
                occurrences.append(Occurrence(
                    e.index, e.method, e.domain, e.url, "Request Cookie", key, str(c.get("value", ""))
                ))
        for c in e.res_cookies:
            if str(c.get("name", "")) == key:
                occurrences.append(Occurrence(
                    e.index, e.method, e.domain, e.url, "Response Cookie", key, str(c.get("value", ""))
                ))

    occurrences.sort(key=lambda o: o.entry_index)
    _mark_changes(occurrences)
    return occurrences


def _truncate(text: str) -> str:
    if len(text) <= BODY_PREVIEW_LENGTH:
        return text
    return text[:BODY_PREVIEW_LENGTH] + "..."


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
        for qp in e.query_params:
            v = str(qp.get("value", ""))
            if needle in v.lower():
                matches.append(Occurrence(e.index, e.method, e.domain, e.url, "Query Param", str(qp.get("name", "")), v))
        for c in e.req_cookies:
            v = str(c.get("value", ""))
            if needle in v.lower():
                matches.append(Occurrence(e.index, e.method, e.domain, e.url, "Request Cookie", str(c.get("name", "")), v))
        for c in e.res_cookies:
            v = str(c.get("value", ""))
            if needle in v.lower():
                matches.append(Occurrence(e.index, e.method, e.domain, e.url, "Response Cookie", str(c.get("name", "")), v))

        if include_headers:
            for h in e.req_headers:
                v = str(h.get("value", ""))
                if needle in v.lower():
                    matches.append(Occurrence(e.index, e.method, e.domain, e.url, "Request Header", str(h.get("name", "")), v))
            for h in e.res_headers:
                v = str(h.get("value", ""))
                if needle in v.lower():
                    matches.append(Occurrence(e.index, e.method, e.domain, e.url, "Response Header", str(h.get("name", "")), v))

        if include_body:
            if needle in e.req_body.lower():
                matches.append(Occurrence(e.index, e.method, e.domain, e.url, "Request Body", "(body)", _truncate(e.req_body)))
            if needle in e.res_body.lower():
                matches.append(Occurrence(e.index, e.method, e.domain, e.url, "Response Body", "(body)", _truncate(e.res_body)))

    matches.sort(key=lambda o: o.entry_index)
    return matches


def summarize(occurrences: list[Occurrence]) -> dict[str, Any]:
    """Aggregate stats for the metrics row: spread, hosts touched, sources involved."""
    if not occurrences:
        return {"total": 0, "distinct_hosts": 0, "hosts": "", "first_index": None, "last_index": None}

    hosts = sorted({o.host for o in occurrences})
    return {
        "total": len(occurrences),
        "distinct_hosts": len(hosts),
        "hosts": ", ".join(hosts),
        "first_index": occurrences[0].entry_index,
        "last_index": occurrences[-1].entry_index,
    }
