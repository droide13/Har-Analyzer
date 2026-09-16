"""Pure logic for tracing the dissemination history of a query-param/cookie key.

Nothing here imports Streamlit, so the functions are plain, testable
transformations of ParsedEntry lists; tabs.dissemination_ui owns the widgets.

Sightings of a key are grouped by name and ordered by their actual HAR
timestamp (startedDateTime) so first appearance and value drift read as a
timeline. `find_dissemination` then reuses the literal matching primitives
from tabs.shared.search to locate every other place in the HAR (headers, URL,
bodies, other cookies) where any of those values reappear.
"""

from dataclasses import dataclass, field

from core.models import FIELD_MAP, ParsedEntry
from tabs.shared.entry_render import Badge
from tabs.shared.search import (
    MatchReason,
    collect_reasons,
    dedupe_overlapping_reasons,
    COOKIE_LABELS,
    dedupe_redundant_encodings,
    encode_variants,
)

Occurrence = tuple[ParsedEntry, str, str]  # (entry, origin, value)
DisseminationMatch = tuple[ParsedEntry, list[MatchReason]]
Registry = dict[str, list[Occurrence]]

_ATTR_LABELS: dict[str, str] = {
    "url": "URL",
    "domain": "Domain",
    "method": "Method",
    "req_headers_text": "Request Headers",
    "res_headers_text": "Response Headers",
    "req_body": "POST Data",
    "res_body": "Response Body",
    "cookies_text": "Cookies",
    "query_params_text": "Query Params",
}


def attr_label(attr: str) -> str:
    """Human-readable name for a ParsedEntry attribute."""
    return _ATTR_LABELS.get(attr, attr.replace("_", " ").title())


def reason_label(reason: MatchReason) -> str:
    """Field name for display; a cookie hit names its side instead of "Cookies".

    Matching is still per-attribute, so these are two labels over the one
    `cookies_text` field.
    """
    if reason.scope is not None:
        return COOKIE_LABELS[reason.scope]
    return attr_label(reason.attr)


def chronological_key(entry: ParsedEntry) -> tuple[str, int]:
    """Sort key putting entries in real time order.

    ISO 8601 timestamps sort lexically, so the raw string is enough; file
    order breaks ties and carries entries that have no startedDateTime.
    """
    return (entry.started_date_time or "", entry.index)


def collect_occurrences(entries: list[ParsedEntry]) -> Registry:
    """Group every query-param/cookie sighting by key name."""
    registry: Registry = {}
    for entry in entries:
        for qp in entry.query_params:
            name = str(qp.get("name", "")).strip()
            if name:
                registry.setdefault(name, []).append((entry, "Query Param", str(qp.get("value", ""))))
        # Walked per side rather than as one merged list, so a sighting
        # records which side of the exchange the cookie came from.
        for origin, cookies in (
            (COOKIE_LABELS["sent"], entry.req_cookies),
            (COOKIE_LABELS["received"], entry.res_cookies),
        ):
            for cookie in cookies:
                name = str(cookie.get("name", "")).strip()
                if name:
                    registry.setdefault(name, []).append(
                        (entry, origin, str(cookie.get("value", "")))
                    )

    for occurrences in registry.values():
        occurrences.sort(key=lambda occ: chronological_key(occ[0]))
    return registry


def key_options(registry: Registry) -> list[str]:
    """Key names sorted by number of sightings, most active first."""
    return sorted(registry, key=lambda name: len(registry[name]), reverse=True)


def value_timeline(occurrences: list[Occurrence]) -> list[dict[str, object]]:
    """One row per sighting, in timestamp order, flagging value changes."""
    rows: list[dict[str, object]] = []
    previous_value: str | None = None
    for entry, origin, value in occurrences:
        changed = previous_value is not None and value != previous_value
        rows.append(
            {
                "Started": entry.started_date_time or f"(no timestamp, entry #{entry.index})",
                "Origin": origin,
                "Method": entry.method,
                "Host": entry.domain,
                "URL": entry.url,
                "Value": value or "(empty)",
                "Value changed": changed,
            }
        )
        previous_value = value
    return rows


def distinct_values(occurrences: list[Occurrence]) -> list[str]:
    """Unique non-empty values ever seen for this key, in first-seen order."""
    seen: dict[str, None] = {}
    for _entry, _origin, value in occurrences:
        if value:
            seen.setdefault(value, None)
    return list(seen)


def find_dissemination(
    entries: list[ParsedEntry],
    values: list[str],
    encodings: set[str],
) -> list[DisseminationMatch]:
    """Every entry where any of `values` (plain or encoded) appears anywhere.

    `domain` is excluded from the "any" sweep for the same reason it's excluded
    from Network Log's default search scope: it's always a substring of `url`,
    so including it would just duplicate every URL hit.

    Encoded variants depend only on the value and the encoding set, so they're
    computed once up front instead of once per entry.

    Results come back in HAR timestamp order rather than file order, so the
    matching entries read as a timeline that lines up with the value one.
    """
    attrs = [a for a in FIELD_MAP["any"] if a != "domain"]
    prepared = [(value, encode_variants(value, encodings)) for value in values]

    results: list[DisseminationMatch] = []
    for entry in entries:
        reasons: list[MatchReason] = []
        for value, variants in prepared:
            reasons.extend(
                dedupe_overlapping_reasons(collect_reasons(entry, attrs, value, variants))
            )
        if reasons:
            results.append((entry, reasons))
    return sorted(results, key=lambda match: chronological_key(match[0]))


def dissemination_badges(reasons: list[MatchReason]) -> list[Badge]:
    """One badge per distinct field the value hit, so the title shows where it leaked."""
    seen_labels: dict[str, None] = {}
    for reason in reasons:
        seen_labels.setdefault(reason_label(reason), None)
    return [(label, "orange") for label in seen_labels]


def reason_summary(reasons: list[MatchReason]) -> list[dict[str, str]]:
    """One row per (field, value): collapses redundant links of the
    URL-encoding chain and lists other matched forms alongside it."""
    grouped: dict[tuple[str, str], list[str]] = {}
    for reason in reasons:
        key = (reason_label(reason), reason.term)
        forms = grouped.setdefault(key, [])
        form = reason.encoding or "plain"
        if form not in forms:
            forms.append(form)

    rows: list[dict[str, str]] = []
    for (field_name, value), forms in sorted(grouped.items()):
        forms = dedupe_redundant_encodings(forms)
        forms_sorted = sorted(forms, key=lambda f: (f != "plain", f))
        rows.append({"Field": field_name, "Value": value, "Forms": ", ".join(forms_sorted)})
    return rows


@dataclass
class _DomainBucket:
    """Accumulator for one domain's hits; kept separate from the output rows
    so the row dicts stay plain data and need no casts to sort."""

    domain: str
    entries: int = 0
    fields: set[str] = field(default_factory=set)
    values: set[str] = field(default_factory=set)
    # Label of the earliest cookie hit on this domain; None if the value never
    # reached it as a cookie.
    first_cookie_as: str | None = None


def aggregate_by_domain(matches: list[DisseminationMatch]) -> list[dict[str, object]]:
    """One row per domain: how many entries were hit, which fields, how many distinct values."""
    # `matches` arrives in HAR timestamp order, and within an entry the request
    # is sent before the response returns, so the first cookie hit seen per
    # domain is genuinely the earliest one.
    buckets: dict[str, _DomainBucket] = {}
    for entry, reasons in matches:
        bucket = buckets.setdefault(entry.domain, _DomainBucket(domain=entry.domain))
        bucket.entries += 1
        for reason in reasons:
            bucket.fields.add(reason_label(reason))
            bucket.values.add(reason.term)
            if bucket.first_cookie_as is None and reason.scope is not None:
                bucket.first_cookie_as = reason_label(reason)

    # Sort the buckets, not the rows: the rows are dict[str, object], and
    # sorting those would need a cast to compare the entry counts.
    ordered = sorted(buckets.values(), key=lambda bucket: bucket.entries, reverse=True)
    return [
        {
            "Domain": bucket.domain,
            "Entries Hit": bucket.entries,
            # Blank when the value only ever reached this domain outside a cookie.
            "Cookie origin": bucket.first_cookie_as or "",
            "Fields": ", ".join(sorted(bucket.fields)),
            "Distinct Values Seen": len(bucket.values),
        }
        for bucket in ordered
    ]
