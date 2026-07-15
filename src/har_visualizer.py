"""Fast HAR File Parser — Streamlit app."""

import json
import re
import shlex
from dataclasses import dataclass
from typing import Any

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
    req_body: str
    res_body: str
    raw: dict[str, Any]

def _headers_to_text(headers: list[dict[str, Any]]) -> str:
    return "\n".join(f"{h.get('name', '')}: {h.get('value', '')}" for h in headers)

@st.cache_data(show_spinner=False)
def load_parsed_entries(file_bytes: bytes) -> list[ParsedEntry]:
    """Parse the raw HAR JSON exactly once per uploaded file."""
    har_data = json.loads(file_bytes)
    raw_entries = har_data.get("log", {}).get("entries", [])
    
    parsed = []
    for i, entry in enumerate(raw_entries):
        request = entry.get("request", {}) or {}
        response = entry.get("response", {}) or {}
        content = response.get("content", {}) or {}
        post_data = request.get("postData", {}) or {}
        
        parsed.append(
            ParsedEntry(
                index=i,
                method=str(request.get("method", "")).upper(),
                url=str(request.get("url", "")),
                status=str(response.get("status", "")),
                status_text=str(response.get("statusText", "")),
                mime=str(content.get("mimeType", "")),
                req_headers_text=_headers_to_text(request.get("headers", []) or []),
                res_headers_text=_headers_to_text(response.get("headers", []) or []),
                req_body=str(post_data.get("text", "") or ""),
                res_body=str(content.get("text", "") or ""),
                raw=entry,
            )
        )
    return parsed

# --------------------------------------------------------------------------- 
# Search Logic
# --------------------------------------------------------------------------- 

FIELD_MAP = {
    "url": ["url"],
    "method": ["method"],
    "status": ["status"],
    "mime": ["mime"],
    "reqheader": ["req_headers_text"],
    "resheader": ["res_headers_text"],
    "header": ["req_headers_text", "res_headers_text"],
    "reqbody": ["req_body"],
    "resbody": ["res_body"],
    "body": ["req_body", "res_body"],
    "any": [
        "url", "method", "status", "mime", 
        "req_headers_text", "res_headers_text", 
        "req_body", "res_body"
    ],
}

SCOPE_OPTIONS = {
    "All fields": "any",
    "URL": "url",
    "Method": "method",
    "Status": "status",
    "Headers (req + res)": "header",
    "Body (req + res)": "body",
    "MIME type": "mime",
}

def match_term(entry: ParsedEntry, term: str, default_field: str) -> bool:
    """Checks if a single term matches the entry."""
    # Handle field:value pairs
    if ":" in term and not term.startswith(("http:", "https:")):
        field, value = term.split(":", 1)
        field = field.lower()
        
        if field in FIELD_MAP:
            # Special wildcard logic for HTTP status codes
            if field == "status" and re.fullmatch(r"[1-5]xx", value.lower()):
                return entry.status.startswith(value[0])
            
            attrs = FIELD_MAP[field]
            return any(value.lower() in getattr(entry, attr).lower() for attr in attrs)

    # Fallback to the default scope
    attrs = FIELD_MAP.get(default_field.lower(), FIELD_MAP["any"])
    return any(term.lower() in getattr(entry, attr).lower() for attr in attrs)

def entry_matches(entry: ParsedEntry, query: str, default_field: str, methods: set[str]) -> bool:
    """Checks if an entry matches all conditions (Methods + Implicit AND terms)."""
    if methods and entry.method not in methods:
        return False
    if not query:
        return True

    # Safely split query, preserving quoted strings
    try:
        terms = shlex.split(query)
    except ValueError:
        terms = query.split() # Fallback if quotes are unclosed

    # Implicit AND logic: Every term must match
    return all(match_term(entry, term, default_field) for term in terms)

# --------------------------------------------------------------------------- 
# UI Helpers
# --------------------------------------------------------------------------- 

METHOD_ORDER = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

def status_emoji(status: str) -> str:
    return "🟢" if status.startswith(("2", "3")) else ("🔴" if status else "⚪")

def render_entry(entry: ParsedEntry, matched: bool, highlight_mode: bool, key_prefix: str) -> None:
    request = entry.raw.get("request", {}) or {}
    response = entry.raw.get("response", {}) or {}
    badge = "⭐ " if highlight_mode and matched else ""
    title = f"{badge}{status_emoji(entry.status)} [{entry.status or '—'}] **{entry.method}** {entry.url}"

    with st.expander(title):
        if highlight_mode and matched:
            st.success("Matches current search / filters", icon="⭐")

        req_tab, res_tab, body_tab = st.tabs(["Request Headers", "Response Headers", "Response Body"])
        with req_tab:
            st.json({h.get("name", ""): h.get("value", "") for h in request.get("headers", [])})
        with res_tab:
            st.json({h.get("name", ""): h.get("value", "") for h in response.get("headers", [])})
        with body_tab:
            content = response.get("content", {}) or {}
            st.caption(f"MIME Type: {content.get('mimeType', 'Unknown')}")
            st.text_area(
                "Content",
                value=content.get("text", "No body content."),
                height=250,
                key=f"body_{key_prefix}_{entry.index}",
                disabled=True,
            )

# --------------------------------------------------------------------------- 
# App
# --------------------------------------------------------------------------- 

st.title("⚡ Fast HAR File Parser")

uploaded_file = st.file_uploader("Upload your .har file here", type=["har", "json"])

if uploaded_file is not None:
    try:
        entries = load_parsed_entries(uploaded_file.getvalue())

        with st.sidebar:
            st.header("🔎 Search")
            search_query = st.text_input("Query", "", placeholder='e.g. method:POST login')

            with st.expander("Search syntax help"):
                st.markdown(
                    "- Plain text searches the selected scope below\n"
                    "- Multiple words require all to match (Implicit AND)\n"
                    "- `field:value` restrict search — e.g. `url:api`, `status:4xx`, `mime:json`, `body:token`\n"
                    "- Quote phrases: `body:\"access token\"`\n"
                    "- Fields: `url`, `method`, `status`, `mime`, `reqheader`, `resheader`, `header`, `reqbody`, `resbody`, `body`, `any`"
                )

            scope_label = st.selectbox("Scope for plain (field-less) terms", options=list(SCOPE_OPTIONS.keys()), index=0)
            default_field = SCOPE_OPTIONS[scope_label]

            available_methods = sorted(
                {e.method for e in entries if e.method},
                key=lambda m: (METHOD_ORDER.index(m) if m in METHOD_ORDER else len(METHOD_ORDER), m),
            )
            selected_methods = st.multiselect("Only these HTTP methods", available_methods, default=[])

            highlight_mode = st.checkbox(
                "Highlight matches instead of filtering",
                value=False,
                help="Show every request, but mark the ones matching the search/filters above.",
            )
            page_size = st.number_input("Results per page", min_value=10, max_value=500, value=50, step=10)

        # Apply filtering
        method_set = set(selected_methods)
        
        if highlight_mode:
            display_entries = entries
            match_flags = [entry_matches(e, search_query, default_field, method_set) for e in entries]
            match_count = sum(match_flags)
        else:
            display_entries = [e for e in entries if entry_matches(e, search_query, default_field, method_set)]
            match_flags = [True] * len(display_entries)
            match_count = len(display_entries)

        # Pagination Reset Logic
        filter_signature = (search_query, default_field, tuple(selected_methods), highlight_mode)
        if st.session_state.get("filter_signature") != filter_signature:
            st.session_state.page = 0
            st.session_state.filter_signature = filter_signature

        # Pagination Calcs
        PAGE_SIZE = int(page_size)
        total_pages = max(1, (len(display_entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        if "page" not in st.session_state:
            st.session_state.page = 0
        if st.session_state.page >= total_pages:
            st.session_state.page = max(0, total_pages - 1)

        # Header Stats
        if highlight_mode:
            st.write(f"**{match_count} match(es)** highlighted out of **{len(entries)}** total requests")
        else:
            st.write(f"**Showing {len(display_entries)} results** (Total in file: {len(entries)})")

        # Pagination Controls
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Previous Page", disabled=(st.session_state.page == 0)):
                st.session_state.page -= 1
                st.rerun()
        with col2:
            st.write(f"**Page {st.session_state.page + 1} of {total_pages}**")
        with col3:
            if st.button("Next Page ➡️", disabled=(st.session_state.page >= total_pages - 1)):
                st.session_state.page += 1
                st.rerun()

        st.markdown("---")

        # Render Entries
        start_idx = st.session_state.page * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE

        for entry, matched in zip(display_entries[start_idx:end_idx], match_flags[start_idx:end_idx]):
            render_entry(entry, matched=matched, highlight_mode=highlight_mode, key_prefix=str(start_idx))

    except Exception as exc: 
        st.error(f"Error processing file: {exc}")