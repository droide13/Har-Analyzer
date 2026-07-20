"""Tab class for tracing a key or value's dissemination and changes over time."""

from typing import Any
import streamlit as st
from models import ParsedEntry
from tabs.history_core import (
    Occurrence,
    collect_known_keys,
    find_key_occurrences,
    find_value_occurrences,
    summarize,
)


def _rows_from_occurrences(occurrences: list[Occurrence]) -> list[dict[str, Any]]:
    return [
        {
            "Order": o.entry_index,
            "Changed": "\u26a0\ufe0f Changed" if o.changed_from_previous else "",
            "Source": o.source,
            "Key": o.key,
            "Value": o.value,
            "Method": o.method,
            "Host": o.host,
            "URL": o.url,
        }
        for o in occurrences
    ]


def _render_results(occurrences: list[Occurrence]) -> None:
    if not occurrences:
        st.warning("No matching requests found.")
        return

    summary = summarize(occurrences)
    changes = sum(1 for o in occurrences if o.changed_from_previous)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Occurrences", summary["total"])
    c2.metric("Distinct Hosts", summary["distinct_hosts"])
    c3.metric("Value Changes", changes, delta_color="inverse" if changes else "off")

    st.caption(f"Hosts touched: {summary['hosts']}")

    st.markdown("#### Timeline")
    st.dataframe(_rows_from_occurrences(occurrences), height=700)


class HistoryTab:
    @property
    def title(self) -> str:
        return "History"

    def render(self, entries: list[ParsedEntry]) -> None:
        st.markdown("### Value Dissemination & Change History")
        st.caption(
            "Trace every request that carries a given key or value, in order, "
            "and see whether it changes or spreads to new hosts over time."
        )

        if not entries:
            st.warning("No entries available to analyze.")
            return

        mode = st.radio("Search by", ["Key name", "Value"], horizontal=True, key="history_mode")

        if mode == "Key name":
            known_keys = collect_known_keys(entries)
            if not known_keys:
                st.info("No query params or cookies found.")
                return
            selected_key = st.selectbox("Select key", known_keys)
            occurrences = find_key_occurrences(entries, selected_key)
            _render_results(occurrences)
        else:
            search_value = st.text_input("Value to search for (substring match)")
            c1, c2 = st.columns(2)
            include_headers = c1.checkbox("Include headers", value=True)
            include_body = c2.checkbox("Include request/response bodies", value=False)

            if not search_value:
                st.info("Enter a value to search for.")
                return

            occurrences = find_value_occurrences(entries, search_value, include_headers, include_body)
            _render_results(occurrences)
