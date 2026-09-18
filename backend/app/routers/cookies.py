"""Cookies tab endpoint."""

from fastapi import APIRouter, HTTPException

from app.features.cookies import aggregate_cookie_records, collect_cookie_records
from app.schemas import RecordsView
from app.store import UploadNotFoundError, upload_store

router = APIRouter(prefix="/api/har", tags=["cookies"])


@router.get("/{upload_id}/cookies", response_model=RecordsView)
async def get_cookies(upload_id: str) -> RecordsView:
    """Per-occurrence cookie records plus a name-grouped aggregate."""
    try:
        record = upload_store.get(upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown upload_id") from exc

    records = collect_cookie_records(record.entries)
    metrics = {
        "total": len(records),
        "missing_secure": sum(1 for r in records if not r["Secure"]),
        "missing_http_only": sum(1 for r in records if not r["HttpOnly"]),
    }
    return RecordsView(
        metrics=metrics, records=records, aggregated=aggregate_cookie_records(records)
    )
