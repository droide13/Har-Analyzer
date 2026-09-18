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


# --- Overview ---


class OverviewSummaryModel(BaseModel):
    """Top-level capture metrics: request count, total size, domains, latency."""

    total_requests: int
    total_bandwidth: int
    unique_domains: int
    avg_latency_ms: float


class SubdomainMetricModel(BaseModel):
    """Request count and bandwidth for one subdomain."""

    requests: int
    bytes: int


class RootDomainMetricModel(BaseModel):
    """Aggregated traffic for one root domain, plus its per-subdomain breakdown."""

    requests: int
    bytes: int
    subdomains: dict[str, SubdomainMetricModel]


class OverviewResponse(BaseModel):
    """Everything the Overview tab needs in one call -- the domain map is
    small (bounded by distinct domains, not entries), so sort/limit/drill-down
    interactions happen client-side against this single payload."""

    summary: OverviewSummaryModel
    method_counts: dict[str, int]
    status_counts: dict[str, int]
    domain_map: dict[str, RootDomainMetricModel]
    first_party_domain: str


class ResolveSubdomainsRequest(BaseModel):
    """Body for the opt-in DNS/WHOIS resolution endpoint."""

    subdomains: list[str]


class SubdomainResolutionRow(BaseModel):
    """One row of the DNS + WHOIS resolution result table."""

    subdomain: str
    chain: str
    ips: str
    organization: str


# --- Cookies / Query Params (structurally identical: raw occurrences + a
# name-grouped aggregate, each view choosing which one to display) ---


class RecordsView(BaseModel):
    """Shared response shape for the Cookies and Query Params tabs."""

    metrics: dict[str, int]
    records: list[dict[str, Any]]
    aggregated: list[dict[str, Any]]


# --- Identifiers ---


class IdentifierValueRow(BaseModel):
    """One distinct value seen for an identifier key."""

    value: str
    first_seen_as: str | None
    appearances: int
    length: int
    entropy: float
    domains: str


class IdentifierSummaryRow(BaseModel):
    """One tracked key (query param or cookie name) and its per-value breakdown."""

    key: str
    first_seen_as: str | None
    appearances: int
    unique_values: int
    avg_length: float
    avg_entropy: float
    domains: str
    values: list[IdentifierValueRow]


class IdentifiersResponse(BaseModel):
    """Filtered/sorted identifier candidates, split by section like the original."""

    query_params: list[IdentifierSummaryRow]
    cookies: list[IdentifierSummaryRow]
