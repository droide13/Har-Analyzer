"""Body Fields view logic: one record per JSON request/response body field
(flattened out of nested objects/arrays), plus a path-grouped aggregate.

Mirrors Cookies/Query Params exactly -- the same "one record per occurrence
-> one row per name" shape via the shared aggregation helpers -- except the
"name" here is a dotted JSON path (see app.shared.json_body) rather than a
cookie or query-param name, since a body field has no name of its own until
it's flattened out of its parent object/array.
"""

from typing import Any

from app.core.models import ParsedEntry
from app.shared.aggregation import describe_value, group_by_name, join_distinct
from app.shared.json_body import flatten_json, parse_json_body
from app.shared.search import attr_label


def collect_body_field_records(entries: list[ParsedEntry]) -> list[dict[str, Any]]:
    """One record per JSON body field occurrence across all requests/responses."""
    records: list[dict[str, Any]] = []
    for e in entries:
        for attr, body in (("req_body", e.req_body), ("res_body", e.res_body)):
            parsed = parse_json_body(body)
            if parsed is None:
                continue
            scope = attr_label(attr)
            records.extend(
                {"Name": path, "Value": value, "Scope": scope, "Host": e.domain}
                for path, value in flatten_json(parsed)
                if value
            )
    return records


def aggregate_body_field_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per field path, summarizing Scope/Value across occurrences."""
    aggregated: list[dict[str, Any]] = [
        {
            "Name": name,
            "Scope": join_distinct(items, "Scope"),
            "Value": describe_value({str(i["Value"]) for i in items}),
            "Occurrences": len(items),
            "Hosts": join_distinct(items, "Host"),
        }
        for name, items in group_by_name(records).items()
    ]

    return sorted(aggregated, key=lambda r: r["Occurrences"], reverse=True)
