"""Strictly typed data structures and parsing for HAR files.

Ported from the original Streamlit app's ``core/models.py``. Behavior is
unchanged; the only structural difference is that entry-building is split
out into :func:`build_entries_from_har_data` so callers that already have
the parsed HAR dict (e.g. the upload store) don't have to parse the same
JSON twice.
"""

import json
import math
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Final, cast
from urllib.parse import urlparse

from app.core.app_version import get_app_version

METHOD_ORDER: Final[list[str]] = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

FIELD_MAP: Final[dict[str, list[str]]] = {
    "url": ["url"],
    "domain": ["domain"],
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
    "Domain": "domain",
    "Method": "method",
    "Status": "status",
    "Headers (req + res)": "header",
    "Query Parameters": "query",
    "Cookies": "cookies",
    "Body (req + res)": "body",
    "MIME type": "mime",
}


@dataclass(frozen=True, slots=True)
class ParsedEntry:  # pylint: disable=too-many-instance-attributes
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


@dataclass(frozen=True, slots=True)
class HarAnalysis:  # pylint: disable=too-many-instance-attributes
    """Experiment-level metadata embedded into a HAR file's ``log._analysis``.

    This is intentionally separate from ``ParsedEntry`` (which describes a
    single request/response transaction). A ``HarAnalysis`` describes the
    whole capture/experiment: what was being tested and how, plus any
    free-text notes a human wants to attach to the file itself so the
    context survives even if the file gets renamed or moved later.
    """

    domain: str
    platform: str
    interact: str
    cookies: str
    visit: str
    extra: str
    captured_at: str
    standardized_filename: str
    description: str = ""
    email_used: str = ""
    notes: str = ""
    tool_version: str = field(default_factory=get_app_version)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the plain dict written into ``log._analysis``."""
        return {
            "tool_version": self.tool_version,
            "domain": self.domain,
            "platform": self.platform,
            "interact": self.interact,
            "cookies": self.cookies,
            "visit": self.visit,
            "extra": self.extra,
            "captured_at": self.captured_at,
            "standardized_filename": self.standardized_filename,
            "description": self.description,
            "email_used": self.email_used,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "HarAnalysis":
        """Parse a previously embedded ``log._analysis`` dict back out."""
        return HarAnalysis(
            domain=str(data.get("domain", "")),
            platform=str(data.get("platform", "")),
            interact=str(data.get("interact", "")),
            cookies=str(data.get("cookies", "")),
            visit=str(data.get("visit", "")),
            extra=str(data.get("extra", "")),
            captured_at=str(data.get("captured_at", "")),
            standardized_filename=str(data.get("standardized_filename", "")),
            description=str(data.get("description", "")),
            email_used=str(data.get("email_used", "")),
            notes=str(data.get("notes", "")),
            tool_version=str(data.get("tool_version", get_app_version())),
        )


def get_domain(url: str) -> str:
    """Netloc of a URL, or "unknown" if it can't be parsed."""
    try:
        return urlparse(url).netloc or "unknown"
    except Exception:  # pylint: disable=broad-exception-caught
        return "unknown"


def headers_to_text(headers: list[dict[str, Any]]) -> str:
    """Flatten a HAR header list into "name: value" lines."""
    return "\n".join(f"{h.get('name', '')}: {h.get('value', '')}" for h in headers)


def query_params_to_text(query_params: list[dict[str, Any]]) -> str:
    """Flatten a HAR query-string list into "name: value" lines."""
    return "\n".join(f"{q.get('name', '')}: {q.get('value', '')}" for q in query_params)


def cookies_to_text(req_cookies: list[dict[str, Any]], res_cookies: list[dict[str, Any]]) -> str:
    """Flatten request/response cookies into "[Req]"/"[Res]" tagged lines."""
    req_lines = [f"[Req] {c.get('name', '')}: {c.get('value', '')}" for c in req_cookies]
    res_lines = [f"[Res] {c.get('name', '')}: {c.get('value', '')}" for c in res_cookies]
    return "\n".join(req_lines + res_lines)


def list_to_safe_dict(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse a name/value item list into a dict, keeping repeats as lists."""
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
    """Human-readable size, e.g. "1.5 KB"."""
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


def resolve_initiator_url(initiator: dict[str, Any], stack_frames: list[dict[str, Any]]) -> str:
    """The URL of whatever actually caused this request.

    Chrome's HAR export only populates the top-level ``_initiator.url`` for
    a ``type: "parser"`` initiator (an HTML/CSS tag directly referencing the
    resource); for ``type: "script"`` -- the common case for anything a
    tracking/ad script fetched -- that field is empty and the calling
    script's URL only exists as the innermost frame of the call stack
    (``stack.callFrames[0]``). Falling back to it is what makes chasing a
    chain of script-initiated requests back to their origin possible at all.
    """
    url = str(initiator.get("url", "") or "")
    if url:
        return url
    if stack_frames:
        return str(stack_frames[0].get("url", "") or "")
    return ""


def build_entries_from_har_data(har_data: dict[str, Any]) -> list[ParsedEntry]:
    """Parse ``log.entries`` out of an already-loaded HAR dict.

    Split out from :func:`load_parsed_entries` so a caller that also needs
    the raw dict (the upload store) can parse the JSON once and reuse it,
    instead of paying for ``json.loads`` twice on a 100-200MB file.
    """
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
        initiator_stack = flatten_initiator_stack(cast(dict[str, Any] | None, initiator.get("stack")))

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
                initiator_url=resolve_initiator_url(initiator, initiator_stack),
                initiator_stack=initiator_stack,
                raw=entry,
                req_headers=req_h,
                res_headers=res_h,
                query_params=qp,
                req_cookies=req_c,
                res_cookies=res_c,
            )
        )
    return parsed


def load_parsed_entries(file_bytes: bytes) -> list[ParsedEntry]:
    """Load a HAR file's bytes and parse its entries."""
    return build_entries_from_har_data(cast(dict[str, Any], json.loads(file_bytes)))


def load_raw_har(file_bytes: bytes) -> dict[str, Any]:
    """Load a HAR file's full JSON structure, unmodified.

    Unlike :func:`load_parsed_entries` (which flattens each entry into a
    ``ParsedEntry``), this keeps the original top-level structure --
    including ``log.creator``, ``log.pages``, and any existing
    ``log._analysis`` -- so it can be edited and written back out as a
    valid HAR file.
    """
    return cast(dict[str, Any], json.loads(file_bytes))


def get_embedded_analysis(har_data: dict[str, Any]) -> HarAnalysis | None:
    """Read back a previously embedded ``log._analysis``, if present."""
    log_data = cast(dict[str, Any], har_data.get("log", {}) or {})
    raw_analysis = log_data.get("_analysis")
    if not isinstance(raw_analysis, dict):
        return None
    return HarAnalysis.from_dict(cast(dict[str, Any], raw_analysis))


def embed_analysis(har_data: dict[str, Any], analysis: HarAnalysis) -> dict[str, Any]:
    """Return a new HAR dict with ``log._analysis`` set to ``analysis``.

    The input dict is left untouched (deep-copied) so callers can safely
    compare "before" and "after" state, e.g. for an overwrite confirmation.
    """
    updated = deepcopy(har_data)
    log_data = cast(dict[str, Any], updated.setdefault("log", {}))
    log_data["_analysis"] = analysis.to_dict()
    return updated


def serialize_har(har_data: dict[str, Any]) -> bytes:
    """Serialize a HAR dict back to downloadable JSON bytes."""
    return json.dumps(har_data, indent=2, ensure_ascii=False).encode("utf-8")
