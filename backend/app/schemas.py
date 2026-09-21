"""Pydantic response models for the HAR API."""

from typing import Any

from pydantic import BaseModel


class SessionMetadata(BaseModel):
    """Best-effort session summary for the persistent header above the tabs --
    domain/platform/interaction/cookies/visit/extra come from the filename
    convention (``None`` if the filename doesn't follow it), captured_at from
    the traffic itself so it's always available regardless of naming."""

    domain: str
    platform: str | None
    interaction: str | None
    cookies: str | None
    visit: str | None
    extra: str | None
    captured_at: str | None
    filename_valid: bool


class UploadResponse(BaseModel):
    """Result of a successful HAR upload."""

    upload_id: str
    filename: str
    entry_count: int
    session_metadata: SessionMetadata


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
    # 1-indexed page numbers containing at least one highlighted match,
    # across the whole filtered set -- not just the current page -- so the
    # UI can offer direct jump buttons. Empty whenever no highlight query
    # is active.
    highlighted_pages: list[int] = []


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
    # Original, unmodified HAR entry JSON -- backs the Timing/Details tabs
    # (connection info, cache, per-phase timings, redirect URL, ...), the
    # same way tabs/shared/entry_render.py's _render_timing_tab/
    # _render_details_tab reach into ``entry.raw`` for fields that don't
    # otherwise have a place on ParsedEntry.
    raw: dict[str, Any]


# --- Overview ---


class OverviewSummaryModel(BaseModel):
    """Top-level capture metrics: request count, total size, domains, latency."""

    total_requests: int
    total_bandwidth: int
    sized_requests: int
    unique_domains: int
    avg_latency_ms: float


class SubdomainMetricModel(BaseModel):
    """Request count and bandwidth for one subdomain."""

    requests: int
    bytes: int
    sized_requests: int


class RootDomainMetricModel(BaseModel):
    """Aggregated traffic for one root domain, plus its per-subdomain breakdown."""

    requests: int
    bytes: int
    sized_requests: int
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


# --- Dissemination ---


class DisseminationFirstSeen(BaseModel):
    """Where/when a traced key's earliest sighting occurred."""

    origin: str
    when: str
    method: str
    domain: str
    value: str


class DisseminationTimelineResponse(BaseModel):
    """Always-live (not gated behind Search): sighting count + value timeline
    for one traced key. ``timeline`` rows keep the original's display-ready
    keys (Started/Origin/Method/Host/URL/Value/"Value changed"), the same
    loose-dict convention as RecordsView."""

    sightings: int
    distinct_values: int
    origins: list[str]
    first_seen: DisseminationFirstSeen
    timeline: list[dict[str, Any]]


class DisseminationSearchRequest(BaseModel):
    """Body for the explicit "Search dissemination" scan.

    ``narrow``/``highlight`` ride along so the whole scan-plus-filter
    happens in one request; they're cheap relative to the scan itself and
    keeping them server-side keeps app.shared.search as the one place the
    query mini-language is implemented.
    """

    key: str
    encodings: list[str]
    narrow: str = ""
    highlight: str = ""


class DisseminationMatchRow(BaseModel):
    """One matching entry: its Network-Log-shaped summary (reused so the
    frontend's row/detail-panel components need no dissemination-specific
    variant) plus which fields it matched through."""

    entry: EntrySummary
    badges: list[str]
    reasons: list[dict[str, str]]


class DisseminationSearchResponse(BaseModel):
    """The full dissemination scan result: domain aggregate + matching entries."""

    by_domain: list[dict[str, Any]]
    matches: list[DisseminationMatchRow]


# --- Metadata ---


class HarAnalysisModel(BaseModel):  # pylint: disable=too-many-instance-attributes
    """Mirrors core.models.HarAnalysis.to_dict()."""

    tool_version: str
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


class MetadataDetected(BaseModel):
    """What the backend derived from the HAR's own traffic."""

    first_request_domain: str
    captured_at: str | None
    domain_options: list[str]


class MetadataResponse(BaseModel):
    """Everything the Metadata tab needs to render its detected-info banner and form."""

    detected: MetadataDetected
    existing_analysis: HarAnalysisModel | None


class GenerateMetadataRequest(BaseModel):  # pylint: disable=too-many-instance-attributes
    """Body for the "Generate standardized file" action."""

    domain: str
    platform: str
    interact: str
    cookies: str
    visit: str
    extra: str = ""
    captured_at: str  # ISO 8601; parsed the same way HAR's own timestamps are
    description: str = ""
    email_used: str = ""
    notes: str = ""


class GenerateMetadataResponse(BaseModel):
    """The standardized filename and the analysis record just embedded."""

    filename: str
    analysis: HarAnalysisModel


class NamingOptions(BaseModel):
    """label tables from app.shared.naming, single source of truth for the
    Metadata form's Platform/Interaction/Cookie/Visit selects."""

    platform: dict[str, str]
    interact: dict[str, str]
    cookies: dict[str, str]
    visit: dict[str, str]
