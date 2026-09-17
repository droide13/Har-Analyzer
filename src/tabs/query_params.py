"""Tab class for showing stored HAR query string parameters."""

from typing import Any

import streamlit as st

from core.models import ParsedEntry
from tabs.shared.aggregation import describe_value, group_by_name


def _describe_categorical(values: set[str]) -> str:
    if len(values) == 1:
        return f"Always {next(iter(values))}"
    return "Mixed"


def _aggregate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


class QueryParamsTab:
    """Tab for displaying HAR query parameters."""

    @property
    def title(self) -> str:
        """Return tab title."""
        return "Query Params"

    def render(self, entries: list[ParsedEntry]) -> None:
        """Render query parameter statistics and dataframes."""
        st.markdown("### Query Parameters list")

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

        if not records:
            st.success("No query string parameters found.")
            return

        unique_names = len({r["Name"] for r in records})
        empty_values = sum(1 for r in records if not r["Value"])

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Params", len(records))
        c2.metric("Unique Param Names", unique_names)
        c3.metric("Empty Values", empty_values)

        view = st.radio(
            "View",
            ["Aggregated by name", "All records"],
            horizontal=True,
            key="query_params_view_toggle",
        )

        if view == "Aggregated by name":
            st.markdown("#### Query Param Behavior Summary")
            st.caption(
                "One row per param name. Method shows 'Mixed' if the param appears "
                "under more than one HTTP method; Value shows the shared value or "
                "how many distinct values were seen."
            )
            st.dataframe(_aggregate(records), height=700)
        else:
            st.markdown("#### Complete Query Parameter Registry Matrix")
            st.dataframe(records, height=700)
