"""Shared expander rendering for a single HAR entry: title, badges, and detail tabs.

Used by both the Requests tab (network log) and the Dissemination tab, so the
"one row = one expander with Request/Response detail" UI only exists once.
Callers supply their own badges and can inject extra leading tabs (e.g. a
"Matches" tab) without duplicating the standard Request/Response tab set.
"""

from typing import Any, Callable, cast

import streamlit as st

from core.models import ParsedEntry, list_to_safe_dict

Badge = tuple[str, str]  # (text, style) where style is "blue" or "orange"


def status_emoji_and_color(status: str) -> tuple[str, str]:
    """Emoji + color name for a status code, shared across tabs."""
    is_ok = status.startswith(("2", "3"))
    color = "green" if is_ok else ("red" if status else "grey")
    emoji = "\U0001f7e2" if is_ok else ("\U0001f534" if status else "\u26aa")
    return emoji, color


def render_badges(badges: list[Badge]) -> str:
    """Render (text, style) badges as trailing colored markdown spans."""
    return "".join(f" :{style}-background[{text}]" for text, style in badges)


def render_title(entry: ParsedEntry, badges: list[Badge]) -> str:
    """Standard expander title: status emoji/color + method + URL + badges."""
    emoji, color = status_emoji_and_color(entry.status)
    status_text = f":{color}[[{entry.status or '\u2014'}]]"
    safe_url = entry.url.replace("[", "\\[").replace("]", "\\]")
    return f"{emoji} {status_text} **{entry.method}** {safe_url}{render_badges(badges)}"


def _render_headers_tab(headers: list[dict[str, Any]]) -> None:
    st.json({str(h.get("name", "")): str(h.get("value", "")) for h in headers})


def _render_post_data_tab(entry: ParsedEntry) -> None:
    st.json(entry.req_body) if entry.req_body else st.info("No POST body found.")


def _render_query_and_cookies_tab(entry: ParsedEntry) -> None:
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


def _render_response_body_tab(entry: ParsedEntry, key_prefix: str) -> None:
    response = cast(dict[str, Any], entry.raw.get("response", {}) or {})
    content = cast(dict[str, Any], response.get("content", {}) or {})
    st.caption(f"MIME Type: {content.get('mimeType', 'Unknown')}")
    st.text_area(
        "Content",
        value=str(content.get("text", "No body content.")),
        height=200,
        key=f"{key_prefix}_body_{entry.index}",
        disabled=True,
    )


def render_entry_expander(
    entry: ParsedEntry,
    key_prefix: str,
    badges: list[Badge],
    leading_tabs: dict[str, Callable[[], None]] | None = None,
) -> None:
    """One expander for an entry: title/badges + optional extra tabs + standard detail tabs."""
    title = render_title(entry, badges)
    leading_tabs = leading_tabs or {}

    with st.expander(title, key=f"{key_prefix}_expander_{entry.index}"):
        tab_names = list(leading_tabs.keys()) + ["Request Headers"]
        if entry.method == "POST":
            tab_names.append("Post data")
        tab_names.extend(["Query & Cookies", "Response Headers", "Response Body"])

        tabs = dict(zip(tab_names, st.tabs(tab_names)))

        for name, render_fn in leading_tabs.items():
            with tabs[name]:
                render_fn()

        with tabs["Request Headers"]:
            _render_headers_tab(entry.req_headers)

        if "Post data" in tabs:
            with tabs["Post data"]:
                _render_post_data_tab(entry)

        with tabs["Query & Cookies"]:
            _render_query_and_cookies_tab(entry)

        with tabs["Response Headers"]:
            _render_headers_tab(entry.res_headers)

        with tabs["Response Body"]:
            _render_response_body_tab(entry, key_prefix)
