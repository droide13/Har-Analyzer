"""Tab class for tracing the dissemination history of a query-param/cookie key.

Groups every sighting of a key by name, orders sightings by their actual HAR
timestamp (startedDateTime) to show first appearance and value drift over
time, then - only when the user explicitly asks - reuses the literal
matching primitives from tabs.shared.search to find every other place in the
HAR (headers, URL, bodies, other cookies) where any of those values reappear.

The dissemination scan is deliberately gated behind a button: it's an O(entries
x values x encodings) substring scan and re-running it on every widget
interaction (e.g. expanding a row) noticeably slows the page.
"""

from typing import cast

import streamlit as st

from core.models import FIELD_MAP, ParsedEntry
from tabs.shared.entry_render import Badge, render_entry_expander
from tabs.shared.search import (
    ENCODING_OPTIONS,
    MatchReason,
    collect_reasons,
    dedupe_overlapping_reasons,
    dedupe_redundant_encodings,
    encode_variants,
)

Occurrence = tuple[ParsedEntry, str, str]  # (entry, origin, value)
DisseminationMatch = tuple[ParsedEntry, list[MatchReason]]

_ATTR_LABELS: dict[str, str] = {
    "url": "URL",
    "domain": "Domain",
    "method": "Method",
    "req_headers_text": "Request Headers",
    "res_headers_text": "Response Headers",
    "req_body": "POST Data",
    "res_body": "Response Body",
    "cookies_text": "Cookies",
    "query_params_text": "Query Params",
}


def _attr_label(attr: str) -> str:
    return _ATTR_LABELS.get(attr, attr.replace("_", " ").title())


def _collect_occurrences(entries: list[ParsedEntry]) -> dict[str, list[Occurrence]]:
    """Group every query-param/cookie sighting by key name."""
    registry: dict[str, list[Occurrence]] = {}
    for entry in entries:
        for qp in entry.query_params:
            name = str(qp.get("name", "")).strip()
            if name:
                registry.setdefault(name, []).append((entry, "query", str(qp.get("value", ""))))
        for cookie in (*entry.req_cookies, *entry.res_cookies):
            name = str(cookie.get("name", "")).strip()
            if name:
                registry.setdefault(name, []).append(
                    (entry, "cookie", str(cookie.get("value", "")))
                )

    # Order sightings by real timestamp when present (ISO 8601 sorts lexically),
    # falling back to file order for entries missing startedDateTime.
    for occurrences in registry.values():
        occurrences.sort(key=lambda occ: (occ[0].started_date_time or "", occ[0].index))
    return registry


def _key_options(registry: dict[str, list[Occurrence]]) -> list[str]:
    """Key names sorted by number of sightings, most active first."""
    return sorted(registry, key=lambda name: len(registry[name]), reverse=True)


def _value_timeline(occurrences: list[Occurrence]) -> list[dict[str, object]]:
    """One row per sighting, in timestamp order, flagging value changes."""
    rows: list[dict[str, object]] = []
    previous_value: str | None = None
    for entry, origin, value in occurrences:
        changed = previous_value is not None and value != previous_value
        rows.append(
            {
                "Started": entry.started_date_time or f"(no timestamp, entry #{entry.index})",
                "Origin": origin,
                "Method": entry.method,
                "Host": entry.domain,
                "URL": entry.url,
                "Value": value or "(empty)",
                "Value changed": changed,
            }
        )
        previous_value = value
    return rows


def _distinct_values(occurrences: list[Occurrence]) -> list[str]:
    """Unique non-empty values ever seen for this key, in first-seen order."""
    seen: dict[str, None] = {}
    for _entry, _origin, value in occurrences:
        if value:
            seen.setdefault(value, None)
    return list(seen)


def _find_dissemination(
    entries: list[ParsedEntry],
    values: list[str],
    encodings: set[str],
) -> list[DisseminationMatch]:
    """Every entry where any of `values` (plain or encoded) appears anywhere.

    `domain` is excluded from the "any" sweep here for the same reason it's
    excluded from Network Log's default search scope: it's always a substring
    of `url`, so including it would just duplicate every URL hit.
    """
    attrs = [a for a in FIELD_MAP["any"] if a != "domain"]
    results: list[DisseminationMatch] = []
    for entry in entries:
        reasons: list[MatchReason] = []
        for value in values:
            variants = encode_variants(value, encodings)
            reasons.extend(
                dedupe_overlapping_reasons(collect_reasons(entry, attrs, value, variants))
            )
        if reasons:
            results.append((entry, reasons))
    return results


def _dissemination_badges(reasons: list[MatchReason]) -> list[Badge]:
    """One badge per distinct attribute the value hit, so the title shows where it leaked."""
    seen_attrs: dict[str, None] = {}
    for reason in reasons:
        seen_attrs.setdefault(reason.attr, None)
    return [(_attr_label(attr), "orange") for attr in seen_attrs]


def _reason_summary(reasons: list[MatchReason]) -> list[dict[str, str]]:
    """One row per (field, value): collapses redundant links of the
    URL-encoding chain and lists other matched forms alongside it."""
    grouped: dict[tuple[str, str], list[str]] = {}
    for reason in reasons:
        key = (_attr_label(reason.attr), reason.term)
        forms = grouped.setdefault(key, [])
        form = reason.encoding or "plain"
        if form not in forms:
            forms.append(form)

    rows: list[dict[str, str]] = []
    for (field, value), forms in sorted(grouped.items()):
        forms = dedupe_redundant_encodings(forms)
        forms_sorted = sorted(forms, key=lambda f: (f != "plain", f))
        rows.append({"Field": field, "Value": value, "Forms": ", ".join(forms_sorted)})
    return rows


def _render_matches_tab(reasons: list[MatchReason]) -> None:
    """Leading tab explaining which field(s)/encoding(s) matched for this entry."""
    st.dataframe(_reason_summary(reasons), height=150)


def _aggregate_by_domain(matches: list[DisseminationMatch]) -> list[dict[str, object]]:
    """One row per domain: how many entries were hit, which fields, how many distinct values."""
    domains: dict[str, dict[str, object]] = {}
    for entry, reasons in matches:
        bucket = domains.setdefault(
            entry.domain,
            {"Domain": entry.domain, "Entries": 0, "_fields": set(), "_values": set()},
        )
        bucket["Entries"] = cast(int, bucket["Entries"]) + 1
        for reason in reasons:
            cast(set[str], bucket["_fields"]).add(_attr_label(reason.attr))
            cast(set[str], bucket["_values"]).add(reason.term)

    rows: list[dict[str, object]] = [
        {
            "Domain": bucket["Domain"],
            "Entries Hit": bucket["Entries"],
            "Fields": ", ".join(sorted(cast(set[str], bucket["_fields"]))),
            "Distinct Values Seen": len(cast(set[str], bucket["_values"])),
        }
        for bucket in domains.values()
    ]
    return sorted(rows, key=lambda r: cast(int, r["Entries Hit"]), reverse=True)


class HistoryTab:
    """Tab for tracing when and where a query-param/cookie key was disseminated."""

    @property
    def title(self) -> str:
        """Return tab title."""
        return "ID history & dissemination"

    def render(self, entries: list[ParsedEntry]) -> None:
        """Render the key picker, value timeline, and (on demand) dissemination results."""
        st.markdown("### Identifier Dissemination History")
        st.caption(
            "Pick a query-param or cookie key to see how its value evolved over "
            "time, then search the whole HAR for every place that value shows "
            "up - headers, URLs, bodies, other cookies - beyond its original key."
        )

        registry = _collect_occurrences(entries)
        if not registry:
            st.success("No query parameters or cookies found to trace.")
            return

        selected_key = st.selectbox(
            "Key to trace", _key_options(registry), key="history_key_select"
        )
        if not selected_key:
            return

        occurrences = registry[selected_key]
        distinct_values = _distinct_values(occurrences)
        origins = sorted({occ[1] for occ in occurrences})

        col1, col2, col3 = st.columns(3)
        col1.metric("Sightings", len(occurrences))
        col2.metric("Distinct Values", len(distinct_values))
        col3.metric("Source", " & ".join(origins))

        first_entry, _origin, first_value = occurrences[0]
        when = first_entry.started_date_time or f"entry #{first_entry.index} (no timestamp)"
        st.info(
            f"First seen at {when} ({first_entry.method} {first_entry.domain}) "
            f"with value `{first_value or '(empty)'}`."
        )

        st.markdown("#### Value Timeline")
        st.caption(
            "One row per sighting, ordered by HAR timestamp. 'Value changed' flags "
            "a sighting whose value differs from the one immediately before it."
        )
        st.dataframe(_value_timeline(occurrences), height=300)

        if not distinct_values:
            return

        st.markdown("#### Dissemination")
        st.caption(
            "This scans every field of every entry and is not run automatically. "
            "Choose optional encodings, then click Search."
        )

        with st.form(key="history_dissemination_form"):
            encodings = st.multiselect(
                "Also match encoded/hashed forms of the value(s)",
                options=ENCODING_OPTIONS,
                key="history_encodings",
            )
            search_clicked = st.form_submit_button("Search dissemination")

        results_key = f"history_matches::{selected_key}"
        if search_clicked:
            with st.spinner("Scanning HAR entries..."):
                st.session_state[results_key] = _find_dissemination(
                    entries, distinct_values, set(encodings)
                )

        matches = cast(list[DisseminationMatch] | None, st.session_state.get(results_key))
        if matches is None:
            st.caption("No search run yet for this key.")
            return
        if not matches:
            st.info("No further dissemination found beyond the key's own occurrences.")
            return

        st.markdown("##### By Domain")
        st.caption(
            "Aggregated view: which hosts received/echoed this value, in how many "
            "entries, through which fields."
        )
        st.dataframe(_aggregate_by_domain(matches), height=250)

        st.markdown("##### Matching Entries")
        for entry, reasons in matches:
            render_entry_expander(
                entry,
                key_prefix="history",
                badges=_dissemination_badges(reasons),
                leading_tabs={"Matches": lambda r=reasons: _render_matches_tab(r)},
            )
