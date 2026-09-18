"""Query Params tab endpoint."""

from fastapi import APIRouter, HTTPException

from app.features.query_params import aggregate_query_param_records, collect_query_param_records
from app.schemas import RecordsView
from app.store import UploadNotFoundError, upload_store

router = APIRouter(prefix="/api/har", tags=["query-params"])


@router.get("/{upload_id}/query-params", response_model=RecordsView)
async def get_query_params(upload_id: str) -> RecordsView:
    try:
        record = upload_store.get(upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown upload_id") from exc

    records = collect_query_param_records(record.entries)
    metrics = {
        "total": len(records),
        "unique_names": len({r["Name"] for r in records}),
        "empty_values": sum(1 for r in records if not r["Value"]),
    }
    return RecordsView(
        metrics=metrics, records=records, aggregated=aggregate_query_param_records(records)
    )
