"""Main tab responsible for rendering interactive network transaction rows."""

from typing import Any, cast

import streamlit as st

from core.models import METHOD_ORDER, SCOPE_OPTIONS, ParsedEntry, list_to_safe_dict
from tabs.networklog.search import ENCODING_OPTIONS, MatchReason, entry_matches

_ATTR_LABELS: dict[str, str] = {
    "url": "URL",
    "method": "Method",
    "status": "Status",
    "req_headers": "Request Headers",
    "res_headers": "Response Headers",
    "req_body": "POST Data",
    "res_body": "Response Body",
    "req_cookies": "Request Cookies",
    "res_cookies": "Response Cookies",
    "query_params": "Query Params",
}


def _attr_label(attr: str) -> str:
    return _ATTR_LABELS.get(attr, attr.replace("_", " ").title())


def _format_reason(reason: MatchReason) -> str:
    label = _attr_label(reason.attr)
    return f"{label} ({reason.encoding})" if reason.encoding else label


def _reason_summary(reasons: list[MatchReason]) -> str:
    return ", ".join(sorted({_format_reason(r) for r in reasons}))


class RequestsTab:
    @property
    def title(self) -> str:
        return "Network Log"

    def _render_pagination_controls(self, curr_p: int, total_p: int, key_suffix: str) -> None:
        c_prev, c_mid, c_next = st.columns([1, 2, 1])
        with c_prev:
            if st.button(
                "Previous",
                disabled=(curr_p == 0),
                key=f"btn_prev_{key_suffix}",
                icon=":material/chevron_left:",
            ):
                st.session_state["req_page"] = curr_p - 1
                st.rerun()
        with c_mid:
            st.markdown(
                f"<p style='text-align:center;'>Page {curr_p + 1} of {total_p}</p>",
                unsafe_allow_html=True,
            )
        with c_next:
            if st.button(
                "Next",
                disabled=(curr_p >= total_p - 1),
                key=f"btn_next_{key_suffix}",
                icon=":material/chevron_right:",
            ):
                st.session_state["req_page"] = curr_p + 1
                st.rerun()

    def _render_row(
        self,
        entry: ParsedEntry,
        key_prefix: str,
        filter_reasons: list[MatchReason],
        highlight_reasons: list[MatchReason],
    ) -> None:

        response = cast(dict[str, Any], entry.raw.get("response", {}) or {})
        status_color = (
            "green" if entry.status.startswith(("2", "3")) else ("red" if entry.status else "grey")
        )
        emoji = "🟢" if entry.status.startswith(("2", "3")) else ("🔴" if entry.status else "⚪")
        status_text = f":{status_color}[[{entry.status or '—'}]]"

        badges: list[str] = []
        if entry.req_cookies:
            badges.append(f"ReqCookies: {len(entry.req_cookies)}")
        if entry.res_cookies:
            badges.append(f"SetCookies: {len(entry.res_cookies)}")
        badge_text = f" :blue-background[{' | '.join(badges)}]" if badges else ""

        match_text = (
            f" :blue-background[Matched via: {_reason_summary(filter_reasons)}]"
            if filter_reasons
            else ""
        )
        highlight_text = (
            f" :orange-background[Highlighted via: {_reason_summary(highlight_reasons)}]"
            if highlight_reasons
            else ""
        )

        title = (
            f"{emoji} {status_text} **{entry.method}** "
            f"{entry.url.replace('[', '\\[').replace(']', '\\]')}"
            f"{badge_text}{match_text}{highlight_text}"
        )

        with st.expander(title, key=f"expander_{entry.index}"):
            # Dynamically build the tab names based on the HTTP method
            tab_names = ["Request Headers"]
            if entry.method == "POST":
                tab_names.append("Post data")
            tab_names.extend(["Query & Cookies", "Response Headers", "Response Body"])

            # Render the tabs and map them to a dictionary
            # st.tabs returns list[DeltaGenerator], zip maps str -> DeltaGenerator
            tabs = dict(zip(tab_names, st.tabs(tab_names)))

            # Populate tabs safely
            with tabs["Request Headers"]:
                st.json(
                    {str(h.get("name", "")): str(h.get("value", "")) for h in entry.req_headers}
                )

            if "Post data" in tabs:
                with tabs["Post data"]:
                    if entry.req_body:
                        st.json(entry.req_body)
                    else:
                        st.info("No POST body found.")
            with tabs["Query & Cookies"]:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Query Parameters")
                    (
                        st.json(list_to_safe_dict(entry.query_params))
                        if entry.query_params
                        else st.caption("No parameters.")
                    )
                with col2:
                    st.markdown("#### Cookie Metadata")
                    if entry.req_cookies or entry.res_cookies:
                        st.json(
                            {
                                "Sent Cookies": list_to_safe_dict(entry.req_cookies),
                                "Set Cookies": list_to_safe_dict(entry.res_cookies),
                            }
                        )
                    else:
                        st.caption("No cookie data.")
            with tabs["Response Headers"]:
                st.json(
                    {str(h.get("name", "")): str(h.get("value", "")) for h in entry.res_headers}
                )
            with tabs["Response Body"]:
                content = cast(dict[str, Any], response.get("content", {}) or {})
                st.caption(f"MIME Type: {content.get('mimeType', 'Unknown')}")
                st.text_area(
                    "Content",
                    value=str(content.get("text", "No body content.")),
                    height=200,
                    key=f"body_{key_prefix}_{entry.index}",
                    disabled=True,
                )

    def render(self, entries: list[ParsedEntry]) -> None:
        st.markdown("### Filter, Query & Highlight Controls")

        with st.expander("Learn How to Search (Negations, Field Filters, etc.)", expanded=False):
            st.markdown("""
            You can type raw words or build highly advanced filter terms inside the fields below:
            
            * **Free Text:** Searches the default field scope selected in the dropdown (e.g., `api/v1`).
            * **Negation (`-`):** Exclude items by adding a minus symbol before a term (e.g., `-status:200` or `-google`).
            * **Force Target Fields:** Bypass the dropdown mapping by prefixes:
              * `url:google` — Only match requests where the URL contains 'google'
              * `cookies:session` — Search cookies for 'session'
              * `status:4xx` or `status:404` — Match status classes or exact codes
              * `method:POST` — Match HTTP method
              * `header:authorization` — Search request/response headers
              * `body:token` — Search query strings, POST payloads, or responses
            """)

        with st.expander("Search Options Panel", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                f_query = st.text_input(
                    "Filter Query (Discards entries)", value="", key="req_f_query"
                )
                h_query = st.text_input(
                    "Highlight Query (Highlights matching background)", value="", key="req_h_query"
                )
            with col2:
                scope_label = st.selectbox(
                    "Text scope mapping", list(SCOPE_OPTIONS.keys()), index=0, key="req_scope"
                )
                df_field = SCOPE_OPTIONS[scope_label]
                methods = sorted(
                    {e.method for e in entries if e.method},
                    key=lambda m: (
                        METHOD_ORDER.index(m) if m in METHOD_ORDER else len(METHOD_ORDER),
                        m,
                    ),
                )
                selected_m = st.multiselect(
                    "Methods target", methods, default=[], key="req_methods"
                )

            st.markdown("#### Also match encoded/hashed forms of each term")
            enc_cols = st.columns(len(ENCODING_OPTIONS))
            selected_encodings: set[str] = set()
            for col, name in zip(enc_cols, ENCODING_OPTIONS):
                with col:
                    if st.checkbox(name, value=True, key=f"req_enc_{name}"):
                        selected_encodings.add(name)

        page_size = int(
            st.number_input(
                "Results per page", min_value=10, max_value=500, value=50, step=10, key="req_size"
            )
        )

        filter_results = {
            e.index: entry_matches(e, f_query, df_field, set(selected_m), selected_encodings)
            for e in entries
        }
        filtered = [e for e in entries if filter_results[e.index].matched]

        h_active = bool(h_query.strip())
        highlight_results = (
            {
                e.index: entry_matches(e, h_query, df_field, set(), selected_encodings)
                for e in filtered
            }
            if h_active
            else {}
        )
        flags = (
            [highlight_results[e.index].matched for e in filtered]
            if h_active
            else [False] * len(filtered)
        )

        sig = (f_query, h_query, df_field, tuple(selected_m), tuple(sorted(selected_encodings)))
        if st.session_state.get("req_sig") != sig:
            st.session_state["req_page"] = 0
            st.session_state["req_sig"] = sig

        total_p = max(1, (len(filtered) + page_size - 1) // page_size)
        curr_p = min(st.session_state.get("req_page", 0), total_p - 1)
        st.session_state["req_page"] = max(0, curr_p)
        curr_p = st.session_state["req_page"]

        start, end = curr_p * page_size, (curr_p + 1) * page_size

        if h_active:
            css = [
                f".st-key-expander_{e.index}, .st-key-expander_{e.index} [data-testid='stExpander'] "
                f"{{ background-color: rgba(255, 170, 0, 0.04) !important; border: 2px solid #ffaa00 !important; "
                f"border-left: 8px solid #ffaa00 !important; }}"
                for e, match in zip(filtered[start:end], flags[start:end])
                if match
            ]
            if css:
                st.html(f"<style>{''.join(css)}</style>")

        st.write(
            f"Showing **{len(filtered)}** items (Matches: {sum(flags)} highlighted) out of {len(entries)} total entries."
        )

        if h_active and sum(flags):
            matched_pages = sorted(
                {(i // page_size) + 1 for i, is_hit in enumerate(flags) if is_hit}
            )
            st.caption(
                f"Highlighted matches appear on {len(matched_pages)} page(s): jump directly below."
            )

            jump_cols = st.columns(min(len(matched_pages), 12))
            for i, page_num in enumerate(matched_pages):
                with jump_cols[i % len(jump_cols)]:
                    is_current = page_num - 1 == curr_p
                    if st.button(
                        str(page_num),
                        key=f"jump_page_{page_num}",
                        type="primary" if is_current else "secondary",
                        disabled=is_current,
                    ):
                        st.session_state["req_page"] = page_num - 1
                        st.rerun()

        self._render_pagination_controls(curr_p, total_p, key_suffix="top")

        st.markdown("---")
        for entry in filtered[start:end]:
            self._render_row(
                entry,
                key_prefix=str(start),
                filter_reasons=filter_results[entry.index].reasons,
                highlight_reasons=highlight_results[entry.index].reasons if h_active else [],
            )

        if filtered[start:end]:
            st.markdown("---")
            self._render_pagination_controls(curr_p, total_p, key_suffix="bottom")
