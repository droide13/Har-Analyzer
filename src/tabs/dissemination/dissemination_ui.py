"""Streamlit UI for the Dissemination tab.

All computation lives in tabs.dissemination; this module is widgets and layout.

Streamlit re-runs the script on every widget interaction, and st.tabs renders
every tab's body on every run, so a click here also pays for the other tabs.
Two things keep that in check:

* the encoding checkboxes sit inside an st.form, so ticking them costs
  nothing - the one rerun happens on submit, which is the scan the user asked
  for. They default to checked, so there's no check-all toggle needing to
  take effect mid-form;
* the picker and results sit in an st.fragment (Streamlit >= 1.37), so that
  submit re-runs this block only and leaves the rest of the app alone.

Results are stored under the (key, encodings) pair that produced them, so
changing either invalidates them instead of leaving stale hits on screen.
"""

from typing import cast

import streamlit as st

from core.models import ParsedEntry
from tabs.dissemination.dissemination import (
    DisseminationMatch,
    MatchReason,
    aggregate_by_domain,
    collect_occurrences,
    dissemination_badges,
    distinct_values,
    find_dissemination,
    key_options,
    reason_summary,
    value_timeline,
)
from tabs.shared.entry_render import render_entry_expander
from tabs.shared.search import ENCODING_OPTIONS

Signature = tuple[str, tuple[str, ...]]  # (traced key, chosen encodings)

_RESULTS_KEY = "history_matches"
_COLS_PER_ROW = 3


def _render_search_form() -> tuple[set[str], bool]:
    """Encoding picker and submit button; returns the encodings and whether to scan.

    Form widgets don't rerun on change, so the set is read once, on submit.
    """
    encodings: set[str] = set()

    with st.form("history_search_form", border=False):
        with st.expander(
            "Encodings & Hashes for term matching (all applied by default)", expanded=False
        ):
            # Iterate through options in chunk sizes of _COLS_PER_ROW
            for i in range(0, len(ENCODING_OPTIONS), _COLS_PER_ROW):
                chunk = ENCODING_OPTIONS[i : i + _COLS_PER_ROW]
                # Create a fresh row of uniform columns
                cols = st.columns(_COLS_PER_ROW)
                # Zip stops when the chunk runs out, leaving remaining columns clean and empty
                for col, name in zip(cols, chunk):
                    with col:
                        # Checked by default: tracing an identifier usually wants every
                        # form of it, so unticking a few beats ticking many.
                        if st.checkbox(name, value=True, key=f"history_enc_{name}"):
                            encodings.add(name)

        submitted = st.form_submit_button("Search dissemination", type="primary")

    return encodings, submitted


def _render_matches_tab(reasons: list[MatchReason]) -> None:
    """Leading tab explaining which field(s)/encoding(s) matched for this entry."""
    st.dataframe(reason_summary(reasons), height=150)


@st.fragment
def _render_dissemination(entries: list[ParsedEntry], key: str, values: list[str]) -> None:
    """Picker, scan trigger and results; re-runs on its own without the rest of the app."""
    st.markdown("#### Dissemination")
    st.caption(
        "This scans every field of every entry and is not run automatically. "
        "Untick any encoded/hashed forms you don't want, then click Search."
    )

    encodings, submitted = _render_search_form()
    signature: Signature = (key, tuple(sorted(encodings)))

    if submitted:
        with st.spinner("Scanning HAR entries..."):
            st.session_state[_RESULTS_KEY] = (
                signature,
                find_dissemination(entries, values, encodings),
            )

    stored = cast(
        tuple[Signature, list[DisseminationMatch]] | None, st.session_state.get(_RESULTS_KEY)
    )
    if stored is None or stored[0] != signature:
        st.caption("No search run yet for this key and encoding selection.")
        return

    matches = stored[1]
    if not matches:
        st.info("No further dissemination found beyond the key's own occurrences.")
        return

    st.markdown("##### By Domain")
    st.caption(
        "Aggregated view: which hosts received/echoed this value, in how many "
        "entries, through which fields. Cookie origin is the earliest cookie hit on that host"
    )
    st.dataframe(aggregate_by_domain(matches), height=250)

    st.markdown("##### Matching Entries")
    st.caption("Ordered by HAR timestamp, oldest first.")
    for entry, reasons in matches:
        render_entry_expander(
            entry,
            key_prefix="history",
            badges=dissemination_badges(reasons),
            leading_tabs={"Matches": lambda r=reasons: _render_matches_tab(r)},
        )


class DisseminationTab:
    """Tab for tracing when and where a query-param/cookie key was disseminated."""

    @property
    def title(self) -> str:
        """Return tab title."""
        return "Dissemination"

    def render(self, entries: list[ParsedEntry]) -> None:
        """Render the key picker, value timeline, and (on demand) dissemination results."""
        st.markdown("### Identifier Dissemination History")
        st.caption(
            "Pick a query-param or cookie key to see how its value evolved over "
            "time, then search the whole HAR for every place that value shows "
            "up - headers, URLs, bodies, other cookies - beyond its original key."
        )

        registry = collect_occurrences(entries)
        if not registry:
            st.success("No query parameters or cookies found to trace.")
            return

        selected_key = st.selectbox("Key to trace", key_options(registry), key="history_key_select")
        if not selected_key:
            return

        occurrences = registry[selected_key]
        values = distinct_values(occurrences)
        origins = sorted({occ[1] for occ in occurrences})

        col1, col2, col3 = st.columns(3)
        col1.metric("Sightings", len(occurrences))
        col2.metric("Distinct Values", len(values))
        col3.metric("Source", " & ".join(origins))

        first_entry, first_origin, first_value = occurrences[0]
        when = first_entry.started_date_time or f"entry #{first_entry.index} (no timestamp)"
        st.info(
            f"First seen as a **{first_origin}** at {when} "
            f"({first_entry.method} {first_entry.domain}) "
            f"with value `{first_value or '(empty)'}`."
        )

        st.markdown("#### Value Timeline")
        st.caption(
            "One row per sighting, ordered by HAR timestamp. 'Value changed' flags "
            "a sighting whose value differs from the one immediately before it."
        )
        st.dataframe(value_timeline(occurrences), height=300)

        if values:
            _render_dissemination(entries, selected_key, values)
