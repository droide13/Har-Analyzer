"""Cookies view logic: one record per cookie sighting, plus a name-grouped
aggregate.
"""

from typing import Any

from app.core.models import ParsedEntry
from app.shared.aggregation import describe_value, group_by_name, join_distinct
from app.shared.search import COOKIE_LABELS


def _describe_flag(values: set[bool]) -> str:
    if len(values) == 1:
        return "Always" if next(iter(values)) else "Never"
    return "Mixed"


def collect_cookie_records(entries: list[ParsedEntry]) -> list[dict[str, Any]]:
    """One record per cookie sighting, tagged with which side it came from.

    Scope uses the shared COOKIE_LABELS wording, so a cookie reads the same
    here, in Dissemination's Origin column, and in search match summaries.
    """
    # Time order, not file order, so the first record for a name is its first
    # sighting. Within one entry the request is sent before the response comes
    # back, so walking sent-then-received below keeps that true too.
    in_time_order = sorted(entries, key=lambda e: (e.started_date_time or "", e.index))

    records: list[dict[str, Any]] = []
    for entry in in_time_order:
        for scope, cookies in (
            (COOKIE_LABELS["sent"], entry.req_cookies),
            (COOKIE_LABELS["received"], entry.res_cookies),
        ):
            for cookie in cookies:
                records.append(
                    {
                        "Name": cookie.get("name", "Unnamed"),
                        "Value": cookie.get("value", ""),
                        "Scope": scope,
                        "Secure": cookie.get("secure", False),
                        "HttpOnly": cookie.get("httpOnly", False),
                        "Host": entry.domain,
                    }
                )
    return records


def aggregate_cookie_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per cookie name, summarizing Secure/HttpOnly/Value across occurrences."""
    aggregated: list[dict[str, Any]] = [
        {
            "Name": name,
            # collect_cookie_records returns records in time order and groups
            # preserve it, so items[0] is this cookie's first sighting.
            "First Seen As": items[0]["Scope"],
            "Scope": join_distinct(items, "Scope"),
            "Secure": _describe_flag({bool(i["Secure"]) for i in items}),
            "HttpOnly": _describe_flag({bool(i["HttpOnly"]) for i in items}),
            "Value": describe_value({str(i["Value"]) for i in items}),
            "Occurrences": len(items),
            "Hosts": join_distinct(items, "Host"),
        }
        for name, items in group_by_name(records).items()
    ]

    return sorted(aggregated, key=lambda r: r["Occurrences"], reverse=True)
