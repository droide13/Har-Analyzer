"""Main tab responsible for rendering interactive network transaction rows."""

from typing import Any, cast
import streamlit as st
from models import ParsedEntry, SCOPE_OPTIONS, list_to_safe_dict, METHOD_ORDER
from search import entry_matches

class RequestsTab:
    @property
    def title(self) -> str:
        return "Network Log"

    def _render_row(self, entry: ParsedEntry, key_prefix: str) -> None:
        response = cast(dict[str, Any], entry.raw.get("response", {}) or {})
        status_color = "green" if entry.status.startswith(("2", "3")) else ("red" if entry.status else "grey")
        emoji = "🟢" if entry.status.startswith(("2", "3")) else ("🔴" if entry.status else "⚪")
        status_text = f":{status_color}[[{entry.status or '—'}]]"
        
        badges: list[str] = []
        if entry.req_cookies: badges.append(f"ReqCookies: {len(entry.req_cookies)}")
        if entry.res_cookies: badges.append(f"SetCookies: {len(entry.res_cookies)}")
        badge_text = f" :blue-background[{' | '.join(badges)}]" if badges else ""
        
        title = f"{emoji} {status_text} **{entry.method}** {entry.url.replace('[', '\\[').replace(']', '\\]')}{badge_text}"

        with st.expander(title, key=f"expander_{entry.index}"):
            req_tab, qp_tab, res_tab, body_tab = st.tabs([
                "Request Headers", "Query & Cookies", "Response Headers", "Response Body"
            ])
            with req_tab:
                st.json({str(h.get("name", "")): str(h.get("value", "")) for h in entry.req_headers})
            with qp_tab:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Query Parameters")
                    st.json(list_to_safe_dict(entry.query_params)) if entry.query_params else st.caption("No parameters.")
                with col2:
                    st.markdown("#### Cookie Metadata")
                    if entry.req_cookies or entry.res_cookies:
                        st.json({
                            "Sent Cookies": list_to_safe_dict(entry.req_cookies),
                            "Set Cookies": list_to_safe_dict(entry.res_cookies)
                        })
                    else:
                        st.caption("No cookie data.")
            with res_tab:
                st.json({str(h.get("name", "")): str(h.get("value", "")) for h in entry.res_headers})
            with body_tab:
                content = cast(dict[str, Any], response.get("content", {}) or {})
                st.caption(f"MIME Type: {content.get('mimeType', 'Unknown')}")
                st.text_area("Content", value=str(content.get("text", "No body content.")), height=200, key=f"body_{key_prefix}_{entry.index}", disabled=True)

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
                f_query = st.text_input("Filter Query (Discards entries)", value="", key="req_f_query")
                h_query = st.text_input("Highlight Query (Highlights matching background)", value="", key="req_h_query")
            with col2:
                scope_label = st.selectbox("Text scope mapping", list(SCOPE_OPTIONS.keys()), index=0, key="req_scope")
                df_field = SCOPE_OPTIONS[scope_label]
                methods = sorted({e.method for e in entries if e.method}, key=lambda m: (METHOD_ORDER.index(m) if m in METHOD_ORDER else len(METHOD_ORDER), m))
                selected_m = st.multiselect("Methods target", methods, default=[], key="req_methods")

        page_size = int(st.number_input("Results per page", min_value=10, max_value=500, value=50, step=10, key="req_size"))
        filtered = [e for e in entries if entry_matches(e, f_query, df_field, set(selected_m))]
        
        h_active = bool(h_query.strip())
        flags = [entry_matches(e, h_query, df_field, set()) for e in filtered] if h_active else [False] * len(filtered)
        
        sig = (f_query, h_query, df_field, tuple(selected_m))
        if st.session_state.get("req_sig") != sig:
            st.session_state["req_page"] = 0
            st.session_state["req_sig"] = sig

        total_p = max(1, (len(filtered) + page_size - 1) // page_size)
        curr_p = min(st.session_state.get("req_page", 0), total_p - 1)
        st.session_state["req_page"] = max(0, curr_p)
        curr_p = st.session_state["req_page"]

        start, end = curr_p * page_size, (curr_p + 1) * page_size
        
        if h_active:
            css = [f".st-key-expander_{e.index}, .st-key-expander_{e.index} [data-testid='stExpander'] {{ background-color: rgba(255, 170, 0, 0.04) !important; border: 2px solid #ffaa00 !important; border-left: 8px solid #ffaa00 !important; }}" for e, match in zip(filtered[start:end], flags[start:end]) if match]
            if css: st.html(f"<style>{''.join(css)}</style>")

        st.write(f"Showing **{len(filtered)}** items (Matches: {sum(flags)} highlighted) out of {len(entries)} total entries.")

        c_prev, c_mid, c_next = st.columns([1, 2, 1])
        with c_prev:
            if st.button("⬅️ Previous", disabled=(curr_p == 0), key="btn_prev"):
                st.session_state["req_page"] = curr_p - 1
                st.rerun()
        with c_mid:
            st.markdown(f"<p style='text-align:center;'>Page {curr_p + 1} of {total_p}</p>", unsafe_allow_html=True)
        with c_next:
            if st.button("Next ➡️", disabled=(curr_p >= total_p - 1), key="btn_next"):
                st.session_state["req_page"] = curr_p + 1
                st.rerun()

        st.markdown("---")
        for entry in filtered[start:end]:
            self._render_row(entry, key_prefix=str(start))