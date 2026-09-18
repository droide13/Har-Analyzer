"""HAR upload and Network Log endpoints.

Filtering/highlighting semantics here are a direct port of the Streamlit
app's Network Log tab (``tabs/networklog.py``): a filter query discards
non-matching entries, an independent highlight query flags matches within
what's left, both share the same scope/method/encoding controls, and
``entry_matches``/``summarize_reasons`` from ``app.shared.search`` do the
actual matching -- unchanged from the original.
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile

from app.core.models import METHOD_ORDER, ParsedEntry
from app.schemas import EntriesPage, EntryDetail, EntrySummary, HeaderPair, UploadResponse
from app.shared.search import ENCODING_OPTIONS, entry_matches, summarize_reasons
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
    )


@router.get("/{upload_id}/entries", response_model=EntriesPage)
async def list_entries(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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

    filter_results = {e.index: entry_matches(e, q, scope, method_set, encoding_set) for e in entries}
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
        items.append(
            EntrySummary(
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
                req_cookie_count=len(entry.req_cookies),
                res_cookie_count=len(entry.res_cookies),
                filter_summary=summarize_reasons(filter_reasons) if q.strip() else None,
                highlighted=highlighted,
                highlight_summary=(
                    summarize_reasons(highlight_result.reasons)
                    if highlighted and highlight_result
                    else None
                ),
            )
        )

    # highlighted_count above only covers the current page; recompute over
    # the full filtered set so the UI can show a true total, not a per-page one.
    total_highlighted = (
        sum(1 for e in filtered if highlight_results[e.index].matched) if h_active else 0
    )

    return EntriesPage(
        total=len(entries),
        filtered=len(filtered),
        highlighted=total_highlighted,
        page=current_page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get("/{upload_id}/entries/{index}", response_model=EntryDetail)
async def get_entry_detail(upload_id: str, index: int) -> EntryDetail:
    """Full request/response detail for one entry, for the row detail panel."""
    record = _get_record(upload_id)
    entry: ParsedEntry | None = next((e for e in record.entries if e.index == index), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="Unknown entry index")

    def as_pairs(items: list[dict[str, object]]) -> list[HeaderPair]:
        return [HeaderPair(name=str(i.get("name", "")), value=str(i.get("value", ""))) for i in items]

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
    )


@router.get("/meta/methods", response_model=list[str])
async def list_method_order() -> list[str]:
    """The canonical HTTP method ordering, so the frontend doesn't hardcode it."""
    return METHOD_ORDER


@router.get("/meta/encodings", response_model=list[str])
async def list_encoding_options() -> list[str]:
    """The canonical encoding/hash checkbox list, so the frontend doesn't hardcode it."""
    return ENCODING_OPTIONS
