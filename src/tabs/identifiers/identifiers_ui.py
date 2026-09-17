"""Tab class for detecting stable identifiers across query params and cookies."""

from typing import Any, Callable

import streamlit as st

from core.models import ParsedEntry
from tabs.identifiers.identifiers import (
    Item,
    TrackedKey,
    ValueOccurrence,
    extract_tracked_keys,
    filter_identifiers,
    get_cookie_items,
    get_query_items,
    sort_identifiers,
)


def _summary_row(tk: TrackedKey) -> dict[str, Any]:
    """Row for the per-key table. First Seen As is omitted for query params,
    which have no side, so that section doesn't carry an empty column."""
    row: dict[str, Any] = {"Key": tk.key}
    if tk.first_seen_as:
        row["First Seen As"] = tk.first_seen_as
    row.update(
        {
            "Appearances": tk.total_appearances,
            "Unique Values": tk.unique_value_count,
            "Avg Length": round(tk.avg_length, 1),
            "Avg Entropy": round(tk.avg_entropy, 2),
            "Domains": ", ".join(sorted(tk.all_domains)),
        }
    )
    return row


def _value_row(v: ValueOccurrence) -> dict[str, Any]:
    """Row for the per-value table, with the side this exact value first appeared on."""
    row: dict[str, Any] = {"Value": v.value}
    if v.first_seen_as:
        row["First Seen As"] = v.first_seen_as
    row.update(
        {
            "Appearances": v.appearances,
            "Length": len(v.value),
            "Entropy": round(v.entropy, 2),
            "Domains": ", ".join(sorted(v.domains)),
        }
    )
    return row


def _render_section(
    entries: list[ParsedEntry],
    get_items: Callable[[ParsedEntry], list[Item]],
    section_label: str,
    sort_by: str,
    **filters: Any,
) -> None:
    tracked = extract_tracked_keys(entries, get_items)
    identifiers = sort_identifiers(filter_identifiers(tracked, **filters), sort_by)

    st.markdown(f"#### {section_label}")
    if not identifiers:
        st.info(f"No matches in {section_label.lower()} at current filter settings.")
        return

    st.dataframe([_summary_row(tk) for tk in identifiers])

    for tk in identifiers:
        _render_value_expander(tk)


def _render_value_expander(tk: TrackedKey) -> None:
    with st.expander(f"Values for `{tk.key}`"):
        st.dataframe(
            [
                _value_row(v)
                for v in sorted(tk.values.values(), key=lambda x: x.appearances, reverse=True)
            ]
        )


class IdentifiersTab:
    """Tab for detecting stable identifiers across query params and cookies."""

    @property
    def title(self) -> str:
        """Tab title"""
        return "Identifiers"

    @st.fragment
    def render(self, entries: list[ParsedEntry]) -> None:
        """Render the filter controls and per-key/value identifier tables.

        Wrapped in st.fragment: the "Search key name" box below is a live
        text_input, and st.tabs renders every tab's body on every run, so
        without this every keystroke here would also re-run Network Log,
        Cookies, Query Params, Overview and Dissemination for no reason.
        """
        st.markdown("### Stable Identifier Detection")
        st.caption(
            "Flags query params and cookies that appear often, take on few "
            "distinct values, and look sufficiently random/long to be a "
            "session, tracking, or auth token \u2014 rather than an ordinary "
            "low-cardinality param like `sort` or `lang`."
        )

        with st.expander("Common noise keys", expanded=False):
            st.markdown("""
                `page`, `limit`, `offset`, `sort`, `order`, `q`, `query`, `lang`, `locale`,
                `cache`, `v`, `version`, `format`, `type`, `action`, `utm_source`,
                `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`
            """)

        if not entries:
            st.warning("No entries available to analyze.")
            return

        search_col, sort_col, exclude_col = st.columns([2, 1, 1])
        name_query = search_col.text_input("Search key name", placeholder="e.g. sess, token, sid")
        sort_by = sort_col.selectbox(
            "Sort by", ["Appearances", "Entropy", "Avg length", "Unique values"]
        )
        exclude_common = exclude_col.checkbox("Exclude common noise keys", value=True)

        c1, c2 = st.columns(2)
        min_appearances = c1.slider("Minimum appearances", min_value=1, max_value=200, value=20)
        max_unique_values = c2.slider("Max unique values", min_value=1, max_value=20, value=5)

        c3, c4 = st.columns(2)
        min_avg_length = c3.slider("Minimum avg value length", min_value=0, max_value=64, value=20)
        min_avg_entropy = c4.slider(
            "Minimum avg entropy (bits/char)", min_value=0.0, max_value=6.0, value=2.5, step=0.1
        )

        filters: dict[str, Any] = {
            "min_appearances": min_appearances,
            "max_unique_values": max_unique_values,
            "min_avg_length": min_avg_length,
            "min_avg_entropy": min_avg_entropy,
            "name_query": name_query,
            "exclude_common": exclude_common,
        }

        _render_section(entries, get_query_items, "Query Parameters", sort_by, **filters)
        st.divider()
        st.caption(
            "First Seen As marks where a cookie turned up first: a Response Cookie "
            "was issued during this capture, a Request Cookie already existed."
        )
        _render_section(entries, get_cookie_items, "Cookies", sort_by, **filters)
