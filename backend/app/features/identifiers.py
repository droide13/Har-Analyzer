"""Data structures and extraction/filtering logic for stable identifier
detection. Ported from the Streamlit app's tabs/identifiers/identifiers.py.

Combines four signals to separate real identifiers (session/tracking/auth
tokens) from ordinary low-cardinality params (status, lang, sort order):
appearance count, value cardinality, average value length, and Shannon
entropy (randomness of characters in the value).

Cookie sightings also carry which side of the exchange they came from, so a
key or value can report whether it was first seen on a request (it predates
the capture) or in a Set-Cookie response (it was issued during the capture).
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable

from app.core.models import ParsedEntry
from app.shared.search import COOKIE_LABELS

# One sighting: the item dict plus which side it came from. Query params have
# no side, so their scope is None.
Item = tuple[str | None, dict[str, Any]]

COMMON_NOISE_KEYS: frozenset[str] = frozenset(
    {
        "page",
        "limit",
        "offset",
        "sort",
        "order",
        "q",
        "query",
        "lang",
        "locale",
        "cache",
        "v",
        "version",
        "format",
        "type",
        "action",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
    }
)


@dataclass(slots=True)
class ValueOccurrence:
    """One distinct value seen for a key, with count + domains it appeared on."""

    value: str
    appearances: int = 0
    domains: set[str] = field(default_factory=set[str])
    # Which side this exact value was first seen on; None for query params.
    first_seen_as: str | None = None

    @property
    def entropy(self) -> float:
        """Shannon entropy of this value's characters."""
        return shannon_entropy(self.value)


@dataclass(slots=True)
class TrackedKey:
    """Aggregated info for one param/cookie name across the whole HAR."""

    key: str
    total_appearances: int = 0
    values: dict[str, ValueOccurrence] = field(default_factory=dict[str, ValueOccurrence])
    # Which side this key was first seen on; None for query params.
    first_seen_as: str | None = None

    @property
    def unique_value_count(self) -> int:
        """Number of distinct values seen for this key."""
        return len(self.values)

    @property
    def avg_length(self) -> float:
        """Mean value length across all distinct values."""
        if not self.values:
            return 0.0
        return sum(len(v.value) for v in self.values.values()) / len(self.values)

    @property
    def avg_entropy(self) -> float:
        """Mean Shannon entropy across all distinct values."""
        if not self.values:
            return 0.0
        return sum(v.entropy for v in self.values.values()) / len(self.values)

    @property
    def all_domains(self) -> set[str]:
        """Union of every domain any value of this key was seen on."""
        result: set[str] = set()
        for v in self.values.values():
            result |= v.domains
        return result


def shannon_entropy(value: str) -> float:
    """Bits of entropy per character. Random tokens score high; words/enums score low."""
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


def get_query_items(entry: ParsedEntry) -> list[Item]:
    """This entry's query params as scopeless items."""
    return [(None, qp) for qp in entry.query_params]


def get_cookie_items(entry: ParsedEntry) -> list[Item]:
    """Request cookies first: within one entry they are sent before the
    response comes back, so this keeps first-seen ordering honest."""
    return [
        *((COOKIE_LABELS["sent"], c) for c in entry.req_cookies),
        *((COOKIE_LABELS["received"], c) for c in entry.res_cookies),
    ]


def extract_tracked_keys(
    entries: list[ParsedEntry],
    get_items: Callable[[ParsedEntry], list[Item]],
) -> dict[str, TrackedKey]:
    """Walk entries, grouping items by name -> distinct values -> domains/counts."""
    tracked: dict[str, TrackedKey] = {}

    # Time order, not file order, so "first seen" means the earliest sighting
    # rather than whichever entry the capture tool happened to write first.
    in_time_order = sorted(entries, key=lambda e: (e.started_date_time or "", e.index))

    for entry in in_time_order:
        for scope, item in get_items(entry):
            name = str(item.get("name", ""))
            value = str(item.get("value", ""))
            if not name:
                continue

            key_entry = tracked.get(name)
            if key_entry is None:
                key_entry = tracked[name] = TrackedKey(key=name, first_seen_as=scope)
            key_entry.total_appearances += 1

            value_entry = key_entry.values.get(value)
            if value_entry is None:
                value_entry = key_entry.values[value] = ValueOccurrence(
                    value=value, first_seen_as=scope
                )
            value_entry.appearances += 1
            value_entry.domains.add(entry.domain)

    return tracked


def filter_identifiers(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    tracked: dict[str, TrackedKey],
    min_appearances: int,
    max_unique_values: int,
    min_avg_length: int,
    min_avg_entropy: float,
    name_query: str,
    exclude_common: bool,
) -> list[TrackedKey]:
    """Apply all threshold + text filters and return matches."""
    matches: list[TrackedKey] = []
    query_lower = name_query.strip().lower()

    for tk in tracked.values():
        if tk.total_appearances < min_appearances:
            continue
        if tk.unique_value_count > max_unique_values:
            continue
        if tk.avg_length < min_avg_length:
            continue
        if tk.avg_entropy < min_avg_entropy:
            continue
        if exclude_common and tk.key.lower() in COMMON_NOISE_KEYS:
            continue
        if query_lower and query_lower not in tk.key.lower():
            continue
        matches.append(tk)

    return matches


def sort_identifiers(identifiers: list[TrackedKey], sort_by: str) -> list[TrackedKey]:
    """Sort identifiers descending by the chosen metric."""
    sort_keys: dict[str, Callable[[TrackedKey], float]] = {
        "Appearances": lambda tk: tk.total_appearances,
        "Entropy": lambda tk: tk.avg_entropy,
        "Avg length": lambda tk: tk.avg_length,
        "Unique values": lambda tk: tk.unique_value_count,
    }
    return sorted(identifiers, key=sort_keys[sort_by], reverse=True)
