"""Body Fields tab endpoint."""

from fastapi import APIRouter

from app.features.body_fields import (
    aggregate_body_field_records,
    collect_body_field_records,
)
from app.schemas import RecordsView

from ._common import get_record_or_404

router = APIRouter(prefix="/api/har", tags=["body-fields"])


@router.get("/{upload_id}/body-fields", response_model=RecordsView)
async def get_body_fields(upload_id: str) -> RecordsView:
    """Per-occurrence JSON body field records plus a path-grouped aggregate."""
    record = get_record_or_404(upload_id)

    records = collect_body_field_records(record.entries)
    metrics = {
        "total": len(records),
        "unique_paths": len({r["Name"] for r in records}),
        "unique_hosts": len({r["Host"] for r in records}),
    }
    return RecordsView(
        metrics=metrics, records=records, aggregated=aggregate_body_field_records(records)
    )
