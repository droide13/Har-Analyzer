"""Group-by-name aggregation helpers shared by the Cookies and Query Params endpoints.

Both views turn a flat list of "one record per occurrence" dicts into "one
row per name" summaries; this is the part of that shape that's identical
between them (the per-view specifics - which columns to compute - stay in
each router).
"""

from typing import Any


def group_by_name(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group records by their "Name" field, preserving first-seen order."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(str(record["Name"]), []).append(record)
    return groups


def join_distinct(records: list[dict[str, Any]], field: str) -> str:
    """Every distinct value of ``field`` across ``records``, sorted and comma-joined."""
    return ", ".join(sorted({str(record[field]) for record in records}))


def describe_value(values: set[str]) -> str:
    """A single shared value, or how many distinct ones were seen."""
    if len(values) == 1:
        return next(iter(values)) or "(empty)"
    return f"Multiple values ({len(values)})"
