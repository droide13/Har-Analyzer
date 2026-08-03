"""UI presentation component for the Overview / HAR Analytics panel."""

import altair as alt
import streamlit as st

from core.models import ParsedEntry, format_bytes
from tabs.overview.overview import (
    build_domain_map,
    build_subdomain_table_data,
    calculate_overview_summary,
    get_first_party_domain,
    get_method_counts,
    get_status_counts,
    get_top_domains_df,
    resolve_subdomains,
)


class OverviewTab:
    """Summary tab UI: request/size/status metrics plus domain explorer."""

    @property
    def title(self) -> str:
        """Tab label shown in the Streamlit tab bar."""
        return "HAR Analytics"

    def render(self, entries: list[ParsedEntry]) -> None:
        """Render the metrics summary, method/status charts, and domain explorer."""
        self._render_metrics_summary(entries)
        st.markdown("---")
        self._render_method_and_status_charts(entries)
        st.markdown("---")
        self._render_domain_explorer(entries)

    def _render_metrics_summary(self, entries: list[ParsedEntry]) -> None:
        """Render top summary metrics cards."""
        st.markdown("### Metrics Summary")

        summary = calculate_overview_summary(entries)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Requests", f"{summary['total_requests']:,}")
        col2.metric("Size", format_bytes(summary["total_bandwidth"]))
        col3.metric("Domains", f"{summary['unique_domains']}")
        col4.metric("Avg Time", f"{summary['avg_latency_ms']:.1f} ms")

    def _render_method_and_status_charts(self, entries: list[ParsedEntry]) -> None:
        """Render HTTP Method and HTTP Status Code distribution bar charts."""
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Methods")
            st.bar_chart(get_method_counts(entries))

        with c2:
            st.markdown("#### Status Codes")
            st.bar_chart(get_status_counts(entries))

    def _render_domain_explorer(self, entries: list[ParsedEntry]) -> None:
        """Root/subdomain traffic breakdown, defaulting to the first-party domain."""
        st.markdown("### Domain and Subdomain Explorer")

        domain_map = build_domain_map(entries)
        domain_options = sorted(domain_map.keys())

        if not domain_options:
            st.info("No domain logs available.")
            return

        # 1. Controls
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

        # 2. Dynamic Domain Chart
        unit_label = "Total Requests" if sort_by == "Requests" else "Total Bytes"
        st.markdown(f"#### Top {chart_limit} Domains by {unit_label}")

        chart_df = get_top_domains_df(domain_map, sort_by, chart_limit)

        if not chart_df.empty:
            dynamic_height = 100 + (len(chart_df) * 30)

            chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    x=alt.X("Value:Q", title=unit_label, scale=alt.Scale(domainMin=0)),
                    y=alt.Y("Domain:N", sort="-x", title="Domain"),
                    tooltip=["Domain", "Value"],
                )
                .properties(height=dynamic_height)
            )

            st.altair_chart(chart)

        # 3. Dropdown Selector
        def format_domain_option(domain_name: str) -> str:
            metrics = domain_map[domain_name]
            return f"{domain_name} ({metrics['requests']} reqs | {format_bytes(metrics['bytes'])})"

        uploaded_filename = st.session_state.get("uploaded_file_name")
        first_party_root = get_first_party_domain(entries, uploaded_filename)
        default_index = (
            domain_options.index(first_party_root) if first_party_root in domain_options else 0
        )

        selected_root = st.selectbox(
            "Inspect Root Domain (Ordered alphabetically):",
            options=domain_options,
            index=default_index,
            format_func=format_domain_option,
        )

        if selected_root:
            data = domain_map[selected_root]

            # Root domain summary cards
            dc1, dc2, dc3 = st.columns(3)
            dc1.metric("Root Requests", f"{data['requests']:,} requests")
            dc2.metric("Total Bandwidth", format_bytes(data["bytes"]))
            dc3.metric("Subdomains Seen", f"{len(data['subdomains'])} subdomains")

            # Subdomain breakdown table
            sub_table_data = build_subdomain_table_data(data, sort_by, format_bytes)

            st.markdown(f"#### Subdomains of `{selected_root}` (Sorted by {sort_by})")

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

            # Subdomain DNS Resolution report
            if selected_root == first_party_root and first_party_root != "unknown":
                st.markdown("---")
                self._render_subdomain_resolution(first_party_root, list(data["subdomains"].keys()))

    def _render_subdomain_resolution(self, first_party_root: str, subdomains: list[str]) -> None:
        """Opt-in DNS + WHOIS report UI."""
        st.markdown(f"#### DNS Resolution for `{first_party_root}` Subdomains")
        st.caption(
            "Fully resolves each subdomain -- following any CNAME chain, the "
            "way `dig` would -- down to an IP address, then looks up who "
            "WHOIS/RDAP says owns that IP."
        )

        if not st.button("Resolve subdomains", key="subdomain_resolve_button"):
            return

        with st.spinner(f"Resolving {len(subdomains)} subdomain(s)..."):
            rows = resolve_subdomains(tuple(sorted(subdomains)))

        st.dataframe(
            rows,
            column_config={
                "Subdomain": st.column_config.TextColumn("Subdomain"),
                "Chain": st.column_config.TextColumn("Resolution Chain"),
                "IPs": st.column_config.TextColumn("IP Address(es)"),
                "Organization": st.column_config.TextColumn("WHOIS Organization"),
            },
            hide_index=True,
        )
