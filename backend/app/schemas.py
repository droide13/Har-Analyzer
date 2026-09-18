"""Pydantic response models for the HAR API."""

from typing import Any

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Result of a successful HAR upload."""

    upload_id: str
    filename: str
    entry_count: int


class EntrySummary(BaseModel):
    """One row of the Network Log list view -- no bodies/headers, those are
    fetched per-row from the detail endpoint only when a row is opened."""

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
    req_cookie_count: int
    res_cookie_count: int
    filter_summary: str | None = None
    highlighted: bool = False
    highlight_summary: str | None = None


class EntriesPage(BaseModel):
    """Paginated, filtered/highlighted Network Log result."""

    total: int
    filtered: int
    highlighted: int
    page: int
    page_size: int
    total_pages: int
    items: list[EntrySummary]


class HeaderPair(BaseModel):
    """A single name/value pair (header, query param, or cookie)."""

    name: str
    value: str


class EntryDetail(BaseModel):
    """Full detail for one HAR entry -- backs the Network Log row detail panel."""

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
    req_headers: list[HeaderPair]
    res_headers: list[HeaderPair]
    query_params: list[HeaderPair]
    req_cookies: list[dict[str, Any]]
    res_cookies: list[dict[str, Any]]
    req_body: str
    res_body: str
    initiator_type: str
    initiator_url: str
    initiator_stack: list[dict[str, Any]]
