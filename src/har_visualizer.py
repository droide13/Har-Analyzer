"""Fast HAR File Parser — Independent Filter/Highlight with Cookie Badges."""

import json
import re
import shlex
from dataclasses import dataclass
from typing import Any, cast

import streamlit as st

st.set_page_config(page_title="Fast HAR Parser", layout="wide")

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParsedEntry:
    """A single HAR entry, flattened into the strings we search over."""

    index: int
    method: str
    url: str
    status: str
    status_text: str
    mime: str
    req_headers_text: str
    res_headers_text: str
    query_params_text: str
    cookies_text: str
    req_body: str
    res_body: str
    raw: dict[str, Any]
    req_headers: list[dict[str, Any]]
    res_headers: list[dict[str, Any]]
    query_params: list[dict[str, Any]]
    req_cookies: list[dict[str, Any]]
    res_cookies: list[dict[str, Any]]


def _headers_to_text(headers: list[dict[str, Any]]) -> str:
    return "\n".join(f"{h.get('name', '')}: {h.get('value', '')}" for h in headers)


def _query_params_to_text(query_params: list[dict[str, Any]]) -> str:
    return "\n".join(f"{q.get('name', '')}: {q.get('value', '')}" for q in query_params)


def _cookies_to_text(req_cookies: list[dict[str, Any]], res_cookies: list[dict[str, Any]]) -> str:
    req_lines = [f"[Req] {c.get('name', '')}: {c.get('value', '')}" for c in req_cookies]
    res_lines = [f"[Res] {c.get('name', '')}: {c.get('value', '')}" for c in res_cookies]
    return "\n".join(req_lines + res_lines)


def _list_to_safe_dict(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Flattens duplicate list values safely into lists or string values."""
    result: dict[str, Any] = {}
    for item in items:
        name = str(item.get("name", ""))
        value = str(item.get("value", ""))
        if name in result:
            if isinstance(result[name], list):
                result[name].append(value)
            else:
                result[name] = [result[name], value]
        else:
            result[name] = value
    return result


@st.cache_data(show_spinner=False)
def load_parsed_entries(file_bytes: bytes) -> list[ParsedEntry]:
    """Parse the raw HAR JSON exactly once per uploaded file."""
    har_data = cast(dict[str, Any], json.loads(file_bytes))
    log_data = cast(dict[str, Any], har_data.get("log", {}))
    raw_entries = cast(list[dict[str, Any]], log_data.get("entries", []))

    parsed: list[ParsedEntry] = []
    for i, entry in enumerate(raw_entries):
        request = cast(dict[str, Any], entry.get("request", {}) or {})
        response = cast(dict[str, Any], entry.get("response", {}) or {})
        content = cast(dict[str, Any], response.get("content", {}) or {})
        post_data = cast(dict[str, Any], request.get("postData", {}) or {})

        req_headers = cast(list[dict[str, Any]], request.get("headers") or [])
        res_headers = cast(list[dict[str, Any]], response.get("headers") or [])
        req_cookies = cast(list[dict[str, Any]], request.get("cookies") or [])
        res_cookies = cast(list[dict[str, Any]], response.get("cookies") or [])
        query_params = cast(list[dict[str, Any]], request.get("queryString") or [])

        parsed.append(
            ParsedEntry(
                index=i,
                method=str(request.get("method", "")).upper(),
                url=str(request.get("url", "")),
                status=str(response.get("status", "")),
                status_text=str(response.get("statusText", "")),
                mime=str(content.get("mimeType", "")),
                req_headers_text=_headers_to_text(req_headers),
                res_headers_text=_headers_to_text(res_headers),
                query_params_text=_query_params_to_text(query_params),
                cookies_text=_cookies_to_text(req_cookies, res_cookies),
                req_body=str(post_data.get("text", "") or ""),
                res_body=str(content.get("text", "") or ""),
                raw=entry,
                req_headers=req_headers,
                res_headers=res_headers,
                query_params=query_params,
                req_cookies=req_cookies,
                res_cookies=res_cookies,
            )
        )
    return parsed


# ---------------------------------------------------------------------------
# Search Logic
# ---------------------------------------------------------------------------

FIELD_MAP: dict[str, list[str]] = {
    "url": ["url"],
    "method": ["method"],
    "status": ["status"],
    "mime": ["mime"],
    "reqheader": ["req_headers_text"],
    "resheader": ["res_headers_text"],
    "header": ["req_headers_text", "res_headers_text"],
    "query": ["query_params_text"],
    "param": ["query_params_text"],
    "cookie": ["cookies_text"],
    "cookies": ["cookies_text"],
    "reqbody": ["req_body"],
    "resbody": ["res_body"],
    "body": ["req_body", "res_body"],
    "any": [
        "url",
        "method",
        "status",
        "mime",
        "req_headers_text",
        "res_headers_text",
        "query_params_text",
        "cookies_text",
        "req_body",
        "res_body",
    ],
}

SCOPE_OPTIONS: dict[str, str] = {
    "All fields": "any",
    "URL": "url",
    "Method": "method",
    "Status": "status",
    "Headers (req + res)": "header",
    "Query Parameters": "query",
    "Cookies": "cookies",
    "Body (req + res)": "body",
    "MIME type": "mime",
}


def match_term(entry: ParsedEntry, term: str, default_field: str) -> bool:
    """Checks if a term matches the entry (supporting negation with `-`)."""
    is_negated = False
    if term.startswith("-") and len(term) > 1:
        is_negated = True
        term = term[1:]

    term = term.strip("'\"")
    matched = False

    if ":" in term and not term.startswith(("http:", "https:")):
        field, value = term.split(":", 1)
        field = field.lower()

        if field in FIELD_MAP:
            if field == "status" and re.fullmatch(r"[1-5]xx", value.lower()):
                matched = entry.status.startswith(value[0])
            else:
                attrs = FIELD_MAP[field]
                matched = any(value.lower() in str(getattr(entry, attr)).lower() for attr in attrs)
        else:
            attrs = FIELD_MAP.get(default_field.lower(), FIELD_MAP["any"])
            matched = any(term.lower() in str(getattr(entry, attr)).lower() for attr in attrs)
    else:
        attrs = FIELD_MAP.get(default_field.lower(), FIELD_MAP["any"])
        matched = any(term.lower() in str(getattr(entry, attr)).lower() for attr in attrs)

    return not matched if is_negated else matched


def entry_matches(entry: ParsedEntry, query: str, default_field: str, methods: set[str]) -> bool:
    """Checks if an entry matches all conditions (Methods + Implicit AND terms)."""
    if methods and entry.method not in methods:
        return False
    if not query:
        return True

    try:
        terms = shlex.split(query)
    except ValueError:
        terms = query.split()

    return all(match_term(entry, term, default_field) for term in terms)


# ---------------------------------------------------------------------------
# UI Helpers & Renderer
# ---------------------------------------------------------------------------

METHOD_ORDER = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def status_emoji(status: str) -> str:
    return "🟢" if status.startswith(("2", "3")) else ("🔴" if status else "⚪")


def render_entry(entry: ParsedEntry, matched: bool, highlight_mode: bool, key_prefix: str) -> None:
    response = cast(dict[str, Any], entry.raw.get("response", {}) or {})

    # 1. Stylize HTTP Status Color
    status_color = (
        "green" if entry.status.startswith(("2", "3")) else ("red" if entry.status else "grey")
    )
    status_text = f":{status_color}[[{entry.status or '—'}]]"

    # 2. Build Cookie & Set-Cookie Badge counts
    cookie_badges: list[str] = []
    if entry.req_cookies:
        cookie_badges.append(f"ReqCookies: {len(entry.req_cookies)}")
    if entry.res_cookies:
        cookie_badges.append(f"SetCookies: {len(entry.res_cookies)}")

    cookie_badge_text = ""
    if cookie_badges:
        cookie_badge_text = f" :blue-background[{' | '.join(cookie_badges)}]"

    # Escape URL brackets to prevent markdown collision breaks
    safe_url = entry.url.replace("[", "\\[").replace("]", "\\]")

    # Assemble header components
    main_title = (f"{status_emoji(entry.status)}"
                  "{status_text} **{entry.method}** {safe_url}{cookie_badge_text}"
                  )

    title = main_title

    # Pass key explicitly to enable targeted custom CSS styling
    with st.expander(title, key=f"expander_{entry.index}"):

        req_tab, qp_tab, res_tab, body_tab = st.tabs(
            ["Request Headers", "Query & Cookies", "Response Headers", "Response Body"]
        )

        with req_tab:
            st.json({str(h.get("name", "")): str(h.get("value", "")) for h in entry.req_headers})

        with qp_tab:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Query Parameters")
                if entry.query_params:
                    st.json(_list_to_safe_dict(entry.query_params))
                else:
                    st.caption("No query parameters found in URL.")
            with col2:
                st.markdown("#### Cookie Metadata")
                if entry.req_cookies or entry.res_cookies:
                    cookie_data: dict[str, dict[str, Any]] = {}
                    if entry.req_cookies:
                        cookie_data["Request Cookies (sent to server)"] = _list_to_safe_dict(
                            entry.req_cookies
                        )
                    if entry.res_cookies:
                        cookie_data["Response Cookies (set by server)"] = _list_to_safe_dict(
                            entry.res_cookies
                        )
                    st.json(cookie_data)
                else:
                    st.caption("No cookie data found.")

        with res_tab:
            st.json({str(h.get("name", "")): str(h.get("value", "")) for h in entry.res_headers})

        with body_tab:
            content = cast(dict[str, Any], response.get("content", {}) or {})
            st.caption(f"MIME Type: {content.get('mimeType', 'Unknown')}")
            st.text_area(
                "Content",
                value=str(content.get("text", "No body content.")),
                height=250,
                key=f"body_{key_prefix}_{entry.index}",
                disabled=True,
            )


# ---------------------------------------------------------------------------
# App Layout
# ---------------------------------------------------------------------------

st.title("⚡ Fast HAR File Parser")

uploaded_file = st.file_uploader("Upload your .har file here", type=["har", "json"])

if uploaded_file is not None:
    try:
        entries = load_parsed_entries(uploaded_file.getvalue())

        with st.sidebar:
            st.header("🔎 Filtering & Search")

            filter_query = st.text_input(
                "Filter Query (Discards non-matches)",
                value="",
                placeholder="e.g. url:api -status:404",
            )

            highlight_query = st.text_input(
                "Highlight Query (Emphasizes matches)",
                value="",
                placeholder="e.g. cookie:admin status:200",
            )

            with st.expander("Search syntax help"):
                st.markdown(
                    "**Basic Syntax Rules:**\n"
                    "- Plain words require all to match (Implicit AND)\n"
                    "- Prefix term with `-` to **negate** (e.g. `-status:5xx`, `-analytics`)\n"
                    '- Use double-quotes for multi-word queries: `"access token"`\n\n'
                    "**Explicit Fields:**\n"
                    "- `status:200` or wildcards: `status:4xx`\n"
                    "- `cookie:session_id` (Request & Response cookies)\n"
                    "- `query:userId` (URL parameters)\n"
                    "- `url:login`, `method:POST`, `mime:json`, `body:token`\n\n"
                    "**Allowed Fields:** `url`, `method`, `status`, `mime`, `reqheader`, `resheader`, `header`, `query`, `cookie`, `reqbody`, `resbody`, `body`, `any`" # pylint
                )

            scope_label = st.selectbox(
                "Scope for plain (field-less) terms", options=list(SCOPE_OPTIONS.keys()), index=0
            )
            default_field = SCOPE_OPTIONS[str(scope_label)]

            available_methods = sorted(
                {e.method for e in entries if e.method},
                key=lambda m: (
                    METHOD_ORDER.index(m) if m in METHOD_ORDER else len(METHOD_ORDER),
                    m,
                ),
            )
            selected_methods = st.multiselect(
                "Only these HTTP methods", available_methods, default=[]
            )

            page_size = st.number_input(
                "Results per page", min_value=10, max_value=500, value=50, step=10
            )

        # 1. Apply Filtering First (removes entries from the view)
        method_set = set(selected_methods)
        filtered_entries = [
            e for e in entries if entry_matches(e, filter_query, default_field, method_set)
        ]

        # 2. Evaluate Highlighting Within Filtered List
        highlight_active = bool(highlight_query.strip())
        if highlight_active:
            match_flags = [
                entry_matches(e, highlight_query, default_field, set()) for e in filtered_entries
            ]
            match_count = sum(match_flags)
        else:
            match_flags = [False] * len(filtered_entries)
            match_count = 0

        # Pagination Reset Logic (tracks both filter + highlight changes)
        filter_signature = (filter_query, highlight_query, default_field, tuple(selected_methods))
        if st.session_state.get("filter_signature") != filter_signature:
            st.session_state["page"] = 0
            st.session_state["filter_signature"] = filter_signature

        # Pagination Calcs
        PAGE_SIZE = int(page_size)
        total_pages = max(1, (len(filtered_entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        if "page" not in st.session_state:
            st.session_state["page"] = 0

        current_page = cast(int, st.session_state["page"])
        if current_page >= total_pages:
            current_page = max(0, total_pages - 1)
            st.session_state["page"] = current_page

        # 3. Dynamic Targeted CSS Injection for highlighted expanders on current page
        start_idx = current_page * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE

        if highlight_active:
            dynamic_css: list[str] = []
            for entry, is_matched in zip(
                filtered_entries[start_idx:end_idx], match_flags[start_idx:end_idx]
            ):
                if is_matched:
                    dynamic_css.append(f"""
                    /* Target container element containing specific expander key */
                    .st-key-expander_{entry.index},
                    .st-key-expander_{entry.index} [data-testid="stExpander"] {{
                        background-color: rgba(255, 170, 0, 0.04) !important;
                        border: 2px solid #ffaa00 !important;
                        border-left: 8px solid #ffaa00 !important;
                        box-shadow: 0 4px 12px rgba(255, 170, 0, 0.08) !important;
                        border-radius: 8px !important;
                        transition: all 0.2s ease-in-out;
                    }}
                    
                    /* Dynamic glow on hover */
                    .st-key-expander_{entry.index}:hover,
                    .st-key-expander_{entry.index} [data-testid="stExpander"]:hover {{
                        background-color: rgba(255, 170, 0, 0.08) !important;
                        box-shadow: 0 6px 16px rgba(255, 170, 0, 0.12) !important;
                    }}
                    """)
            if dynamic_css:
                st.html(f"<style>{''.join(dynamic_css)}</style>")

        # Header Stats
        if highlight_active:
            st.write(
                f"Showing **{len(filtered_entries)}** results with **{match_count}** highlighted "
                f"(Total in file: {len(entries)})"
            )
        else:
            st.write(f"Showing **{len(filtered_entries)}** results (Total in file: {len(entries)})")

        # Pagination Controls
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Previous Page", disabled=current_page == 0):
                st.session_state["page"] = current_page - 1
                st.rerun()
        with col2:
            st.write(f"**Page {current_page + 1} of {total_pages}**")
        with col3:
            if st.button("Next Page ➡️", disabled=current_page >= total_pages - 1):
                st.session_state["page"] = current_page + 1
                st.rerun()

        st.markdown("---")

        # Render Entries
        for entry, is_matched in zip(
            filtered_entries[start_idx:end_idx], match_flags[start_idx:end_idx]
        ):
            render_entry(
                entry,
                matched=is_matched,
                highlight_mode=highlight_active,
                key_prefix=str(start_idx),
            )

    except Exception as exc:
        st.error(f"Error processing file: {exc}")
