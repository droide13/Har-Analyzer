"""Overview panel with charts summarizing status, metrics, and domain/subdomain distribution."""

from typing import TypedDict
import altair as alt
import pandas as pd
import streamlit as st
from models import ParsedEntry, format_bytes

class SubdomainMetric(TypedDict):
    requests: int
    bytes: int

class RootDomainMetric(TypedDict):
    requests: int
    bytes: int
    subdomains: dict[str, SubdomainMetric]

class SubdomainRow(TypedDict):
    Subdomain: str
    Requests: int
    Bytes: int
    Size: str


def _get_base_domain(domain: str) -> str:
    """Extracts the base/root domain (e.g. 'api.github.com' -> 'github.com')."""
    if not domain or domain == "unknown":
        return "unknown"

    parts = domain.lower().split(".")
    if len(parts) <= 2:
        return domain

    # Check for common multi-part suffixes (e.g., co.uk, com.br, gov.uk)
    if len(parts[-2]) <= 3 and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


class OverviewTab:
    @property
    def title(self) -> str:
        return "HAR Analytics"

    def render(self, entries: list[ParsedEntry]) -> None:
        st.markdown("### Metrics Summary")

        total = len(entries)
        # Treat negative sizes (-1 from cache/unknown) as 0
        bandwidth = sum(max(0, e.body_size) + max(0, e.headers_size) for e in entries)
        domains = len({e.domain for e in entries if e.domain})
        avg_latency = (
            sum(e.time_ms for e in entries) / total if total > 0 else 0.0
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Requests", f"{total:,}")
        col2.metric("Size", format_bytes(bandwidth))
        col3.metric("Domains", f"{domains}")
        col4.metric("Avg Time", f"{avg_latency:.1f} ms")

        st.markdown("---")

        # Layout: HTTP Methods & Status Codes
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Methods")
            m_data: dict[str, int] = {}
            for e in entries:
                m_data[e.method] = m_data.get(e.method, 0) + 1
            st.bar_chart(m_data)

        with c2:
            st.markdown("#### Status Codes")
            s_data: dict[str, int] = {}
            for e in entries:
                key = str(e.status) if e.status else "Incomplete"
                s_data[key] = s_data.get(key, 0) + 1
            st.bar_chart(s_data)

        st.markdown("---")
        self._render_domain_explorer(entries)

    def _render_domain_explorer(self, entries: list[ParsedEntry]) -> None:
        st.markdown("### Domain and Subdomain Explorer")

        # 1. Aggregate traffic metrics by Root and Subdomain
        domain_map: dict[str, RootDomainMetric] = {}

        for e in entries:
            domain = e.domain.lower() if e.domain else "unknown"
            base = _get_base_domain(domain)
            
            # Safeguard against -1 cached values here as well
            size = max(0, e.body_size) + max(0, e.headers_size)

            if base not in domain_map:
                domain_map[base] = {"requests": 0, "bytes": 0, "subdomains": {}}

            domain_map[base]["requests"] += 1
            domain_map[base]["bytes"] += size

            if domain not in domain_map[base]["subdomains"]:
                domain_map[base]["subdomains"][domain] = {
                    "requests": 0,
                    "bytes": 0,
                }

            domain_map[base]["subdomains"][domain]["requests"] += 1
            domain_map[base]["subdomains"][domain]["bytes"] += size

        # 2. Controls: Sorting Selector & Chart Limit Slider
        ctrl_col1, ctrl_col2 = st.columns([1, 1])
        with ctrl_col1:
            sort_by = st.radio(
                "Sort Everything By",
                ["Requests", "Bandwidth"],
                horizontal=True,
                key="domain_sort_toggle",
            )
        with ctrl_col2:
            chart_limit = st.slider(
                "Show Top Domains in Chart",
                min_value=5,
                max_value=50,
                value=10,
                step=5,
            )

        # Helper to sort domains dynamically
        def get_root_sort_key(item: tuple[str, RootDomainMetric]) -> int:
            return item[1]["requests"] if sort_by == "Requests" else item[1]["bytes"]

        sorted_domains = sorted(
            domain_map.items(),
            key=get_root_sort_key,
            reverse=True,
        )

        # Dropdown options sorted alphabetically
        domain_options = sorted(domain_map.keys())

        if not domain_options:
            st.info("No domain logs available.")
            return

        # 3. Dynamic Domain Chart
        unit_label = "Total Requests" if sort_by == "Requests" else "Total Bytes"
        st.markdown(f"#### Top {chart_limit} Domains by {unit_label}")
        
        chart_df = pd.DataFrame([
            {
                "Domain": d[0],
                "Value": d[1]["requests"] if sort_by == "Requests" else d[1]["bytes"]
            }
            for d in sorted_domains[:chart_limit]
        ])

        if not chart_df.empty:
            dynamic_height = 100 + (len(chart_df) * 30)

            # Explicitly build a horizontal bar chart with locked left alignment
            chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    # FIX 3: Enforce domainMin=0 to completely block the axis from sliding left
                    x=alt.X("Value:Q", title=unit_label, scale=alt.Scale(domainMin=0)),
                    y=alt.Y("Domain:N", sort="-x", title="Domain"),
                    tooltip=["Domain", "Value"]
                )
                .properties(height=dynamic_height)
            )
            
            st.altair_chart(chart)

        # 4. Dropdown Selector (Alphabetically ordered)
        def format_domain_option(domain_name: str) -> str:
            metrics = domain_map[domain_name]
            return f"{domain_name} ({metrics['requests']} reqs | {format_bytes(metrics['bytes'])})"

        selected_root = st.selectbox(
            "Inspect Root Domain (Ordered alphabetically):",
            options=domain_options,
            format_func=format_domain_option,
        )

        if selected_root:
            data = domain_map[selected_root]

            # Root domain summary cards
            dc1, dc2, dc3 = st.columns(3)
            dc1.metric("Root Requests", f"{data['requests']:,} requests")
            dc2.metric("Total Bandwidth", format_bytes(data["bytes"]))
            dc3.metric("Subdomains Seen", f"{len(data['subdomains'])} subdomains")

            # Subdomain breakdown table (Dynamic sort applied)
            sub_table_data: list[SubdomainRow] = []
            for sub, metrics in data["subdomains"].items():
                sub_table_data.append(
                    {
                        "Subdomain": sub,
                        "Requests": metrics["requests"],
                        "Bytes": metrics["bytes"],
                        "Size": format_bytes(metrics["bytes"]),
                    }
                )

            def get_sub_sort_key(row: SubdomainRow) -> int:
                return row["Requests"] if sort_by == "Requests" else row["Bytes"]

            sub_table_data.sort(
                key=get_sub_sort_key,
                reverse=True,
            )

            st.markdown(f"#### Subdomains of `{selected_root}` (Sorted by {sort_by})")
            
            # Displays human-friendly Size, but uses Bytes internally for sorting
            st.dataframe(
                sub_table_data,
                column_order=["Subdomain", "Requests", "Size"],
                column_config={
                    "Subdomain": st.column_config.TextColumn("Subdomain Address"),
                    "Requests": st.column_config.NumberColumn("Requests", format="%d"),
                    "Size": st.column_config.TextColumn("Total Size"),
                },
                hide_index=True,
            )