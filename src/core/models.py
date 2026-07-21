"""Strictly typed data structures and caching loaders for HAR parsing."""

import json
import math
from dataclasses import dataclass
from typing import Any, Final, cast
from urllib.parse import urlparse

import streamlit as st

METHOD_ORDER: Final[list[str]] = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

FIELD_MAP: Final[dict[str, list[str]]] = {
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

SCOPE_OPTIONS: Final[dict[str, str]] = {
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


@dataclass(frozen=True, slots=True)
class ParsedEntry:
    """Immutable, indexed representation of a singular HAR entry transaction."""

    index: int
    started_date_time: str
    method: str
    url: str
    domain: str
    status: str
    status_text: str
    mime: str
    time_ms: float
    body_size: int
    headers_size: int
    req_headers_text: str
    res_headers_text: str
    query_params_text: str
    cookies_text: str
    req_body: str
    res_body: str
    initiator_type: str
    initiator_url: str
    initiator_stack: list[dict[str, Any]]
    raw: dict[str, Any]
    req_headers: list[dict[str, Any]]
    res_headers: list[dict[str, Any]]
    query_params: list[dict[str, Any]]
    req_cookies: list[dict[str, Any]]
    res_cookies: list[dict[str, Any]]

def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"


def headers_to_text(headers: list[dict[str, Any]]) -> str:
    return "\n".join(f"{h.get('name', '')}: {h.get('value', '')}" for h in headers)


def query_params_to_text(query_params: list[dict[str, Any]]) -> str:
    return "\n".join(f"{q.get('name', '')}: {q.get('value', '')}" for q in query_params)


def cookies_to_text(req_cookies: list[dict[str, Any]], res_cookies: list[dict[str, Any]]) -> str:
    req_lines = [f"[Req] {c.get('name', '')}: {c.get('value', '')}" for c in req_cookies]
    res_lines = [f"[Res] {c.get('name', '')}: {c.get('value', '')}" for c in res_cookies]
    return "\n".join(req_lines + res_lines)


def list_to_safe_dict(items: list[dict[str, Any]]) -> dict[str, Any]:
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


def format_bytes(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"
    size_names = ("B", "KB", "MB", "GB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def flatten_initiator_stack(stack: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Flatten a (possibly chained, async) initiator call stack into one frame list."""
    frames: list[dict[str, Any]] = []
    current = stack
    while current:
        call_frames = cast(list[dict[str, Any]], current.get("callFrames") or [])
        frames.extend(call_frames)
        current = cast(dict[str, Any] | None, current.get("parent"))
    return frames


@st.cache_data(show_spinner=False)
def load_parsed_entries(file_bytes: bytes) -> list[ParsedEntry]:
    har_data = cast(dict[str, Any], json.loads(file_bytes))
    log_data = cast(dict[str, Any], har_data.get("log", {}))
    raw_entries = cast(list[dict[str, Any]], log_data.get("entries", []))

    parsed: list[ParsedEntry] = []
    for i, entry in enumerate(raw_entries):
        request = cast(dict[str, Any], entry.get("request", {}) or {})
        response = cast(dict[str, Any], entry.get("response", {}) or {})
        content = cast(dict[str, Any], response.get("content", {}) or {})
        post_data = cast(dict[str, Any], request.get("postData", {}) or {})
        initiator = cast(dict[str, Any], entry.get("_initiator", {}) or {})

        req_h = cast(list[dict[str, Any]], request.get("headers") or [])
        res_h = cast(list[dict[str, Any]], response.get("headers") or [])
        req_c = cast(list[dict[str, Any]], request.get("cookies") or [])
        res_c = cast(list[dict[str, Any]], response.get("cookies") or [])
        qp = cast(list[dict[str, Any]], request.get("queryString") or [])

        parsed.append(
            ParsedEntry(
                index=i,
                started_date_time=str(entry.get("startedDateTime", "")),
                method=str(request.get("method", "")).upper(),
                url=str(request.get("url", "")),
                domain=get_domain(str(request.get("url", ""))),
                status=str(response.get("status", "")),
                status_text=str(response.get("statusText", "")),
                mime=str(content.get("mimeType", "")),
                time_ms=float(entry.get("time", 0.0) or 0.0),
                body_size=int(response.get("bodySize", 0) or 0),
                headers_size=int(response.get("headersSize", 0) or 0),
                req_headers_text=headers_to_text(req_h),
                res_headers_text=headers_to_text(res_h),
                query_params_text=query_params_to_text(qp),
                cookies_text=cookies_to_text(req_c, res_c),
                req_body=str(post_data.get("text", "") or ""),
                res_body=str(content.get("text", "") or ""),
                initiator_type=str(initiator.get("type", "other")),
                initiator_url=str(initiator.get("url", "")),
                initiator_stack=flatten_initiator_stack(
                    cast(dict[str, Any] | None, initiator.get("stack"))
                ),
                raw=entry,
                req_headers=req_h,
                res_headers=res_h,
                query_params=qp,
                req_cookies=req_c,
                res_cookies=res_c,
            )
        )
    return parsed
