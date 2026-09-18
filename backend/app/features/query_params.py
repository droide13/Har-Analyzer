"""Query Params view logic: one record per query-string param occurrence,
plus a name-grouped aggregate. Ported from the Streamlit app's
tabs/query_params.py.
"""

from typing import Any

from app.core.models import ParsedEntry
from app.shared.aggregation import describe_value, group_by_name


def _describe_categorical(values: set[str]) -> str:
    if len(values) == 1:
        return f"Always {next(iter(values))}"
    return "Mixed"


def collect_query_param_records(entries: list[ParsedEntry]) -> list[dict[str, Any]]:
    """One record per query-string param occurrence across all requests."""
    records: list[dict[str, Any]] = []
    for e in entries:
        for qp in e.query_params:
            records.append(
                {
                    "Name": qp.get("name", "Unnamed"),
                    "Value": qp.get("value", ""),
                    "Method": e.method,
                    "Host": e.domain,
                }
            )
    return records


def aggregate_query_param_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per param name, summarizing Method/Value across occurrences."""
    aggregated: list[dict[str, Any]] = []
    for name, items in group_by_name(records).items():
        method_set: set[str] = {str(i["Method"]) for i in items}
        value_set: set[str] = {str(i["Value"]) for i in items}
        host_set: set[str] = {str(i["Host"]) for i in items}

        aggregated.append(
            {
                "Name": name,
                "Method": _describe_categorical(method_set),
                "Value": describe_value(value_set),
                "Occurrences": len(items),
                "Hosts": ", ".join(sorted(host_set)),
            }
        )

    return sorted(aggregated, key=lambda r: r["Occurrences"], reverse=True)
