"""Query Params view logic: one record per query-string param occurrence,
plus a name-grouped aggregate.
"""

from typing import Any

from app.core.models import ParsedEntry
from app.shared.aggregation import describe_value, group_by_name, join_distinct


def collect_query_param_records(entries: list[ParsedEntry]) -> list[dict[str, Any]]:
    """One record per query-string param occurrence across all requests."""
    return [
        {
            "Name": qp.get("name", "Unnamed"),
            "Value": qp.get("value", ""),
            "Method": e.method,
            "Host": e.domain,
        }
        for e in entries
        for qp in e.query_params
    ]


def aggregate_query_param_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per param name, summarizing Method/Value across occurrences."""
    aggregated: list[dict[str, Any]] = [
        {
            "Name": name,
            "Method": join_distinct(items, "Method"),
            "Value": describe_value({str(i["Value"]) for i in items}),
            "Occurrences": len(items),
            "Hosts": join_distinct(items, "Host"),
        }
        for name, items in group_by_name(records).items()
    ]

    return sorted(aggregated, key=lambda r: r["Occurrences"], reverse=True)
