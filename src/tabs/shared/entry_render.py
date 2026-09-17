"""Shared expander rendering for a single HAR entry: title, badges, and detail tabs.

Used by both the Requests tab (network log) and the Dissemination tab, so the
"one row = one expander with Request/Response detail" UI only exists once.
Callers supply their own badges and can inject extra leading tabs (e.g. a
"Matches" tab) without duplicating the standard Request/Response tab set.
"""

import json
from typing import Any, Callable, cast

import streamlit as st

from core.models import ParsedEntry, list_to_safe_dict

Badge = tuple[str, str]  # (text, style) where style is a Streamlit color name

_TIMING_PHASES = ("blocked", "dns", "connect", "ssl", "send", "wait", "receive")


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


def _format_duration_ms(value: float) -> str:
    """Format a HAR timing value in ms; HAR uses -1 for "not applicable"."""
    return f"{value:.1f} ms" if value >= 0 else "\u2014"


def _render_headers_tab(headers: list[dict[str, Any]]) -> None:
    st.json({str(h.get("name", "")): str(h.get("value", "")) for h in headers})


def _render_post_data_tab(entry: ParsedEntry, key_prefix: str) -> None:
    """Request body: pretty-printed as JSON when it parses, raw text otherwise.

    ``req_body`` is arbitrary request-payload text (JSON, form-encoded,
    plain text, etc.), not guaranteed JSON, so it can't be handed to
    ``st.json`` directly -- that raises on anything that isn't valid JSON.
    """
    if not entry.req_body:
        st.info("No request body found.")
        return
    try:
        st.json(json.loads(entry.req_body))
    except (json.JSONDecodeError, TypeError):
        st.text_area(
            "Raw body",
            value=entry.req_body,
            height=200,
            key=f"{key_prefix}_reqbody_{entry.index}",
            disabled=True,
        )


def _render_query_and_cookies_tab(entry: ParsedEntry) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Query Parameters")
        if entry.query_params:
            st.json(list_to_safe_dict(entry.query_params))
        else:
            st.caption("No parameters.")
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


def _render_initiator_tab(entry: ParsedEntry) -> None:
    st.caption(f"Type: {entry.initiator_type}")
    if entry.initiator_url:
        st.text(f"Source URL: {entry.initiator_url}")
    if not entry.initiator_stack:
        st.caption("No JS call stack available for this request.")
        return
    st.dataframe(
        [
            {
                "Function": frame.get("functionName") or "(anonymous)",
                "URL": frame.get("url", ""),
                "Line": frame.get("lineNumber", ""),
                "Column": frame.get("columnNumber", ""),
            }
            for frame in entry.initiator_stack
        ],
        height=200,
    )


def _render_timing_tab(entry: ParsedEntry) -> None:
    """Per-phase timing breakdown (blocked/dns/connect/ssl/send/wait/receive)."""
    timings = cast(dict[str, Any], entry.raw.get("timings", {}) or {})

    st.caption(f"Started: {entry.started_date_time or 'Unknown'}")
    st.caption(f"Total time: {_format_duration_ms(entry.time_ms)}")

    rows = [
        {"Phase": phase.capitalize(), "Duration": _format_duration_ms(float(timings[phase]))}
        for phase in _TIMING_PHASES
        if phase in timings
    ]
    if rows:
        st.dataframe(rows, height=250, hide_index=True)
    else:
        st.caption("No timing breakdown available for this entry.")


def _render_details_tab(entry: ParsedEntry) -> None:
    """Connection, protocol, payload size, redirect, and cache metadata."""
    request = cast(dict[str, Any], entry.raw.get("request", {}) or {})
    response = cast(dict[str, Any], entry.raw.get("response", {}) or {})
    cache = cast(dict[str, Any], entry.raw.get("cache", {}) or {})

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Connection")
        st.json(
            {
                "Server IP": entry.raw.get("serverIPAddress") or "Unknown",
                "Connection": entry.raw.get("connection") or "Unknown",
                "Request HTTP Version": request.get("httpVersion", "Unknown"),
                "Response HTTP Version": response.get("httpVersion", "Unknown"),
            }
        )
    with col2:
        st.markdown("#### Sizes & Redirect")
        st.json(
            {
                "Request Headers Size": request.get("headersSize", -1),
                "Request Body Size": request.get("bodySize", -1),
                "Response Headers Size": entry.headers_size,
                "Response Body Size": entry.body_size,
                "Redirect URL": response.get("redirectURL") or None,
            }
        )

    if cache:
        st.markdown("#### Cache")
        st.json(cache)


def render_entry_expander(
    entry: ParsedEntry,
    key_prefix: str,
    badges: list[Badge],
    leading_tabs: dict[str, Callable[[], None]] | None = None,
    highlighted: bool = False,
) -> None:
    """One expander for an entry: title/badges + optional extra tabs + standard detail tabs.

    When `highlighted` is True, the whole expander gets a yellow outline so it
    stands out in a long list, in addition to any badges in the title.
    """
    title = render_title(entry, badges)
    leading_tabs = leading_tabs or {}
    container_key = f"{key_prefix}_container_{entry.index}"

    if highlighted:
        st.markdown(
            f"""
            <style>
            .st-key-{container_key} div[data-testid="stExpander"] {{
                border: 2px solid #FFD400;
                border-radius: 8px;
                box-shadow: 0 0 6px rgba(255, 212, 0, 0.5);
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    with st.container(key=container_key):
        with st.expander(title, key=f"{key_prefix}_expander_{entry.index}"):
            tab_names = list(leading_tabs.keys()) + ["Request Headers"]
            if entry.req_body:
                tab_names.append("Post data")
            tab_names.extend(
                [
                    "Query & Cookies",
                    "Response Headers",
                    "Response Body",
                    "Initiator",
                    "Timing",
                    "Details",
                ]
            )

            tabs = dict(zip(tab_names, st.tabs(tab_names)))

            for name, render_fn in leading_tabs.items():
                with tabs[name]:
                    render_fn()

            with tabs["Request Headers"]:
                _render_headers_tab(entry.req_headers)

            if "Post data" in tabs:
                with tabs["Post data"]:
                    _render_post_data_tab(entry, key_prefix)

            with tabs["Query & Cookies"]:
                _render_query_and_cookies_tab(entry)

            with tabs["Response Headers"]:
                _render_headers_tab(entry.res_headers)

            with tabs["Response Body"]:
                _render_response_body_tab(entry, key_prefix)

            with tabs["Initiator"]:
                _render_initiator_tab(entry)

            with tabs["Timing"]:
                _render_timing_tab(entry)

            with tabs["Details"]:
                _render_details_tab(entry)
