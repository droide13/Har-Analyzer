"""Data structures and extraction/filtering logic for stable identifier detection.

Combines four signals to separate real identifiers (session/tracking/auth
tokens) from ordinary low-cardinality params (status, lang, sort order):
appearance count, value cardinality, average value length, and Shannon
entropy (randomness of characters in the value).
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable

from models import ParsedEntry

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

    @property
    def entropy(self) -> float:
        return shannon_entropy(self.value)


@dataclass(slots=True)
class TrackedKey:
    """Aggregated info for one param/cookie name across the whole HAR."""

    key: str
    total_appearances: int = 0
    values: dict[str, ValueOccurrence] = field(default_factory=dict[str, ValueOccurrence])

    @property
    def unique_value_count(self) -> int:
        return len(self.values)

    @property
    def avg_length(self) -> float:
        if not self.values:
            return 0.0
        return sum(len(v.value) for v in self.values.values()) / len(self.values)

    @property
    def avg_entropy(self) -> float:
        if not self.values:
            return 0.0
        return sum(v.entropy for v in self.values.values()) / len(self.values)

    @property
    def all_domains(self) -> set[str]:
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


def get_query_items(entry: ParsedEntry) -> list[dict[str, Any]]:
    return entry.query_params


def get_cookie_items(entry: ParsedEntry) -> list[dict[str, Any]]:
    return entry.req_cookies + entry.res_cookies


def extract_tracked_keys(
    entries: list[ParsedEntry],
    get_items: Callable[[ParsedEntry], list[dict[str, Any]]],
) -> dict[str, TrackedKey]:
    """Walk entries, grouping items by name -> distinct values -> domains/counts."""
    tracked: dict[str, TrackedKey] = {}

    for entry in entries:
        for item in get_items(entry):
            name = str(item.get("name", ""))
            value = str(item.get("value", ""))
            if not name:
                continue

            key_entry = tracked.setdefault(name, TrackedKey(key=name))
            key_entry.total_appearances += 1

            value_entry = key_entry.values.setdefault(value, ValueOccurrence(value=value))
            value_entry.appearances += 1
            value_entry.domains.add(entry.domain)

    return tracked


def filter_identifiers(
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
    sort_keys: dict[str, Callable[[TrackedKey], float]] = {
        "Appearances": lambda tk: tk.total_appearances,
        "Entropy": lambda tk: tk.avg_entropy,
        "Avg length": lambda tk: tk.avg_length,
        "Unique values": lambda tk: tk.unique_value_count,
    }
    return sorted(identifiers, key=sort_keys[sort_by], reverse=True)
