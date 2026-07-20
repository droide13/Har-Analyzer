"""Tab class for showing stored HAR cookies."""

from typing import Any

import streamlit as st

from models import ParsedEntry


def _describe_flag(values: set[bool]) -> str:
    if len(values) == 1:
        return "Always" if next(iter(values)) else "Never"
    return "Mixed"


def _describe_value(values: set[str]) -> str:
    if len(values) == 1:
        return next(iter(values)) or "(empty)"
    return f"Multiple values ({len(values)})"


def _aggregate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        groups.setdefault(str(r["Name"]), []).append(r)

    aggregated: list[dict[str, Any]] = []
    for name, items in groups.items():
        secure_set: set[bool] = {bool(i["Secure"]) for i in items}
        httponly_set: set[bool] = {bool(i["HttpOnly"]) for i in items}
        value_set: set[str] = {str(i["Value"]) for i in items}
        host_set: set[str] = {str(i["Host"]) for i in items}

        aggregated.append(
            {
                "Name": name,
                "Secure": _describe_flag(secure_set),
                "HttpOnly": _describe_flag(httponly_set),
                "Value": _describe_value(value_set),
                "Occurrences": len(items),
                "Hosts": ", ".join(sorted(host_set)),
            }
        )

    return sorted(aggregated, key=lambda r: r["Occurrences"], reverse=True)


class CookiesTab:
    """Tab for displaying HAR cookies."""

    @property
    def title(self) -> str:
        """Return tab title."""
        return "Cookies"

    def render(self, entries: list[ParsedEntry]) -> None:
        """Render cookie statistics and dataframes."""
        st.markdown("### Cookies list")

        records: list[dict[str, Any]] = []
        for e in entries:
            for c in e.req_cookies:
                records.append(
                    {
                        "Name": c.get("name", "Unnamed"),
                        "Value": c.get("value", ""),
                        "Scope": "Sent Cookie",
                        "Secure": c.get("secure", False),
                        "HttpOnly": c.get("httpOnly", False),
                        "Host": e.domain,
                    }
                )
            for c in e.res_cookies:
                records.append(
                    {
                        "Name": c.get("name", "Unnamed"),
                        "Value": c.get("value", ""),
                        "Scope": "Set-Cookie Received",
                        "Secure": c.get("secure", False),
                        "HttpOnly": c.get("httpOnly", False),
                        "Host": e.domain,
                    }
                )

        if not records:
            st.success("No active authentication headers or session tokens found.")
            return

        missing_secure = sum(1 for r in records if not r["Secure"])
        missing_httponly = sum(1 for r in records if not r["HttpOnly"])

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Cookies", len(records))
        c2.metric("Insecure SSL Cookies", missing_secure, delta_color="inverse")
        c3.metric("Missing HttpOnly Protection", missing_httponly, delta_color="inverse")

        view = st.radio(
            "View",
            ["Aggregated by name", "All records"],
            horizontal=True,
            key="cookies_view_toggle",
        )

        if view == "Aggregated by name":
            st.markdown("#### Cookie Behavior Summary")
            st.caption(
                "One row per cookie name. Secure/HttpOnly show 'Mixed' if they "
                "vary across occurrences; Value shows the shared value or how "
                "many distinct values were seen."
            )
            st.dataframe(_aggregate(records), height=700)
        else:
            st.markdown("#### Complete Cookie Registry Matrix")
            st.dataframe(records, height=700)
