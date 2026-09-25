"""Pure logic for tracing the dissemination history of a query-param/cookie key.

Sightings of a key are grouped by name and ordered by their actual HAR
timestamp (startedDateTime) so first appearance and value drift read as a timeline.
``find_dissemination`` then reuses the literal matching primitives from
app.shared.search to locate every other place in the HAR (headers, URL,
bodies, other cookies) where any of those values reappear.
"""

from dataclasses import dataclass, field

from app.core.har_time import format_started_date_time
from app.core.models import FIELD_MAP, ParsedEntry
from app.shared.search import (
    COOKIE_LABELS,
    MatchReason,
    collect_reasons,
    dedupe_overlapping_reasons,
    encode_variants,
    reason_label,
)

Occurrence = tuple[ParsedEntry, str, str]  # (entry, origin, value)
DisseminationMatch = tuple[ParsedEntry, list[MatchReason]]
Registry = dict[str, list[Occurrence]]


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
        # Cookies are walked per side rather than as one merged list, so a
        # sighting records which side of the exchange it came from.
        for origin, items in (
            ("Query Param", entry.query_params),
            (COOKIE_LABELS["sent"], entry.req_cookies),
            (COOKIE_LABELS["received"], entry.res_cookies),
        ):
            for item in items:
                name = str(item.get("name", "")).strip()
                if name:
                    registry.setdefault(name, []).append(
                        (entry, origin, str(item.get("value", "")))
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
        started = (
            format_started_date_time(entry.started_date_time)
            if entry.started_date_time
            else f"(no timestamp, entry #{entry.index})"
        )
        rows.append(
            {
                "Started": started,
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


_MAX_INITIATOR_CHAIN_DEPTH = 25


@dataclass(slots=True)
class InitiatorChainHop:
    """One hop in the chain of requests that (transitively) caused a traced
    sighting. `entry` is only `None` when `found` is False -- the
    initiating URL was never captured in this HAR (a dangling reference),
    not that there wasn't one."""

    found: bool
    entry: ParsedEntry | None
    url: str
    initiator_type: str


def _dangling_hop(url: str, initiator_type: str) -> InitiatorChainHop:
    return InitiatorChainHop(found=False, entry=None, url=url, initiator_type=initiator_type)


def build_initiator_chain(
    entries: list[ParsedEntry], start: ParsedEntry
) -> list[InitiatorChainHop]:
    """Walk backwards from `start` through each entry's initiator_url, one
    hop at a time, to reconstruct which script (transitively) caused it --
    e.g. the page loaded script A, which loaded script B, which made the
    request that first carried this value.

    Each hop looks up the entry that fetched the current one's
    initiator_url -- the latest such entry at or before it in time, since
    that's the one the browser would actually have already loaded by then.
    Returns hops in chronological order (earliest cause first, ending just
    before `start`, which the caller already displays separately). Stops
    when an entry has no initiator_url (top-level navigation), the
    initiating URL was never captured in this HAR (a dangling reference,
    included as the final, unresolved hop), or a cycle/depth limit is hit.
    """
    by_url: dict[str, list[ParsedEntry]] = {}
    for entry in entries:
        by_url.setdefault(entry.url, []).append(entry)
    for group in by_url.values():
        group.sort(key=chronological_key)

    chain: list[InitiatorChainHop] = []
    seen_indices = {start.index}
    current = start

    for _ in range(_MAX_INITIATOR_CHAIN_DEPTH):
        initiator_url = current.initiator_url
        if not initiator_url:
            break

        candidates = by_url.get(initiator_url)
        if not candidates:
            chain.append(_dangling_hop(initiator_url, current.initiator_type))
            break

        current_key = chronological_key(current)
        preceding = [
            e
            for e in candidates
            if chronological_key(e) <= current_key and e.index not in seen_indices
        ]
        if not preceding:
            # Every captured occurrence of this initiator URL happened
            # *after* `current` (or was already visited earlier in this
            # walk) -- there's no candidate that could actually have caused
            # it, so this is a dangling reference, not a cause to report.
            chain.append(_dangling_hop(initiator_url, current.initiator_type))
            break

        next_entry = preceding[-1]
        seen_indices.add(next_entry.index)
        chain.append(
            InitiatorChainHop(
                found=True,
                entry=next_entry,
                url=next_entry.url,
                initiator_type=next_entry.initiator_type,
            )
        )
        current = next_entry

    return list(reversed(chain))


def find_dissemination(
    entries: list[ParsedEntry],
    values: list[str],
    encodings: set[str],
) -> list[DisseminationMatch]:
    """Every entry where any of `values` (plain or encoded) appears anywhere.

    `domain` is excluded from the "any" sweep for the same reason it's excluded
    from Network Log's default search scope: it's always a substring of `url`,
    so including it would just duplicate every URL hit.

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


@dataclass(slots=True)
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

    ordered = sorted(buckets.values(), key=lambda bucket: bucket.entries, reverse=True)
    return [
        {
            "Domain": bucket.domain,
            "Entries Hit": bucket.entries,
            "Cookie origin": bucket.first_cookie_as or "",
            "Fields": ", ".join(sorted(bucket.fields)),
            "Distinct Values Seen": len(bucket.values),
        }
        for bucket in ordered
    ]
