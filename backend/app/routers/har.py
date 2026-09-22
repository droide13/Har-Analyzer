"""HAR upload and Network Log endpoints.

Filtering/highlighting semantics here are a direct port of the Streamlit
app's Network Log tab (``tabs/networklog.py``): a filter query discards
non-matching entries, an independent highlight query flags matches within
what's left, both share the same scope/method/encoding controls, and
``entry_matches``/``summarize_reasons`` from ``app.shared.search`` do the
actual matching -- unchanged from the original.
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile

from app.core.models import METHOD_ORDER, SCOPE_OPTIONS, ParsedEntry, get_embedded_analysis
from app.schemas import (
    EntriesPage,
    EntryDetail,
    EntrySummary,
    HeaderPair,
    SessionMetadata,
    UploadResponse,
)
from app.shared.entry_summary import build_entry_summary
from app.shared.naming import derive_metadata_from_entries, get_attrs_from_har_name
from app.shared.search import ENCODING_OPTIONS, dissemination_badge_labels, entry_matches
from app.store import UploadNotFoundError, UploadRecord, upload_store

router = APIRouter(prefix="/api/har", tags=["har"])


def _get_record(upload_id: str) -> UploadRecord:
    try:
        return upload_store.get(upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown upload_id") from exc


def _parse_csv(value: str | None) -> set[str] | None:
    """``None`` -> caller-defined default; ``""`` -> empty set; else split on commas."""
    if value is None:
        return None
    return {part.strip() for part in value.split(",") if part.strip()}


def _build_session_metadata(record: UploadRecord) -> SessionMetadata:
    """Filename-convention attrs (domain/platform/interaction/cookies/visit/
    extra) plus a capture date, so the header has a date to show even for a
    HAR whose filename doesn't follow the convention.

    The capture date prefers a previously embedded ``log._analysis.captured_at``
    -- it's an authoritative, human-confirmed value -- falling back to
    re-deriving it from the traffic's ``startedDateTime`` only when no such
    analysis has been embedded yet. Live re-detection is otherwise reserved
    for the Metadata tab's generate flow."""
    attrs = get_attrs_from_har_name(record.filename)
    existing = get_embedded_analysis(record.har_data)

    try:
        derived = derive_metadata_from_entries(record.entries)
    except ValueError:
        derived = None

    domain = attrs["domain"] if attrs else (derived.domain if derived else record.filename)
    extra = attrs["extra"] if attrs and attrs["extra"] != "000" else None

    if existing is not None:
        captured_at = existing.captured_at
    else:
        captured_at = derived.captured_at.isoformat() if derived and derived.captured_at else None

    return SessionMetadata(
        domain=domain,
        platform=attrs["platform"] if attrs else None,
        interaction=attrs["interaction"] if attrs else None,
        cookies=attrs["cookies"] if attrs else None,
        visit=attrs["visit"] if attrs else None,
        extra=extra,
        captured_at=captured_at,
        filename_valid=attrs is not None,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_har(file: UploadFile) -> UploadResponse:
    """Accept a .har file, parse it once, and register it for later lookups."""
    file_bytes = await file.read()
    try:
        record = upload_store.add(filename=file.filename or "upload.har", file_bytes=file_bytes)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail=f"Could not parse HAR file: {exc}") from exc
    return UploadResponse(
        upload_id=record.upload_id,
        filename=record.filename,
        entry_count=len(record.entries),
        session_metadata=_build_session_metadata(record),
    )


@router.get("/{upload_id}/entries", response_model=EntriesPage)
async def list_entries(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    upload_id: str,
    q: str = Query(default="", description="Filter query (discards non-matching entries)"),
    h: str = Query(default="", description="Highlight query (flags matches, discards nothing)"),
    scope: str = Query(default="any", description="Default field scope for unprefixed terms"),
    methods: str | None = Query(default=None, description="Comma-separated HTTP methods"),
    encodings: str | None = Query(
        default=None, description="Comma-separated encodings; omit for all, empty string for none"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=10, le=500),
) -> EntriesPage:
    """Filtered, highlighted, paginated Network Log rows."""
    record = _get_record(upload_id)
    entries = record.entries

    method_set = _parse_csv(methods) or set()
    encoding_set = _parse_csv(encodings)
    if encoding_set is None:
        encoding_set = set(ENCODING_OPTIONS)

    filter_results = {
        e.index: entry_matches(e, q, scope, method_set, encoding_set) for e in entries
    }
    filtered = [e for e in entries if filter_results[e.index].matched]

    h_active = bool(h.strip())
    highlight_results = (
        {e.index: entry_matches(e, h, scope, set(), encoding_set) for e in filtered}
        if h_active
        else {}
    )

    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    current_page = min(page, total_pages)
    start, end = (current_page - 1) * page_size, current_page * page_size

    items: list[EntrySummary] = []
    highlighted_count = 0
    for entry in filtered[start:end]:
        highlight_result = highlight_results.get(entry.index)
        highlighted = bool(highlight_result and highlight_result.matched)
        if highlighted:
            highlighted_count += 1
        filter_reasons = filter_results[entry.index].reasons
        summary = build_entry_summary(entry)
        summary.highlighted = highlighted
        # Mirrors Dissemination's badge logic: prefer the highlight query's
        # own reasons when this row is highlighted (the more specific "why"),
        # falling back to the filter query's reasons -- every visible row
        # matched it, if one was given.
        if highlighted and highlight_result:
            summary.badges = dissemination_badge_labels(highlight_result.reasons)
        elif q.strip():
            summary.badges = dissemination_badge_labels(filter_reasons)
        items.append(summary)

    # highlighted_count above only covers the current page; recompute over
    # the full filtered set so the UI can show a true total, not a per-page one.
    total_highlighted = (
        sum(1 for e in filtered if highlight_results[e.index].matched) if h_active else 0
    )

    highlighted_pages: list[int] = []
    if h_active:
        seen_pages = {
            i // page_size + 1
            for i, e in enumerate(filtered)
            if highlight_results[e.index].matched
        }
        highlighted_pages = sorted(seen_pages)

    return EntriesPage(
        total=len(entries),
        filtered=len(filtered),
        highlighted=total_highlighted,
        page=current_page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
        highlighted_pages=highlighted_pages,
    )


@router.get("/{upload_id}/entries/{index}", response_model=EntryDetail)
async def get_entry_detail(upload_id: str, index: int) -> EntryDetail:
    """Full request/response detail for one entry, for the row detail panel."""
    record = _get_record(upload_id)
    entry: ParsedEntry | None = next((e for e in record.entries if e.index == index), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="Unknown entry index")

    def as_pairs(items: list[dict[str, object]]) -> list[HeaderPair]:
        return [
            HeaderPair(name=str(i.get("name", "")), value=str(i.get("value", ""))) for i in items
        ]

    return EntryDetail(
        index=entry.index,
        started_date_time=entry.started_date_time,
        method=entry.method,
        url=entry.url,
        domain=entry.domain,
        status=entry.status,
        status_text=entry.status_text,
        mime=entry.mime,
        time_ms=entry.time_ms,
        body_size=entry.body_size,
        headers_size=entry.headers_size,
        req_headers=as_pairs(entry.req_headers),
        res_headers=as_pairs(entry.res_headers),
        query_params=as_pairs(entry.query_params),
        req_cookies=entry.req_cookies,
        res_cookies=entry.res_cookies,
        req_body=entry.req_body,
        res_body=entry.res_body,
        initiator_type=entry.initiator_type,
        initiator_url=entry.initiator_url,
        initiator_stack=entry.initiator_stack,
        raw=entry.raw,
    )


@router.get("/meta/methods", response_model=list[str])
async def list_method_order() -> list[str]:
    """The canonical HTTP method ordering, so the frontend doesn't hardcode it."""
    return METHOD_ORDER


@router.get("/meta/encodings", response_model=list[str])
async def list_encoding_options() -> list[str]:
    """The canonical encoding/hash checkbox list, so the frontend doesn't hardcode it."""
    return ENCODING_OPTIONS


@router.get("/meta/scopes", response_model=dict[str, str])
async def list_scope_options() -> dict[str, str]:
    """Label -> field-key map for the search scope dropdown, single source of truth."""
    return SCOPE_OPTIONS
