"""Metadata tab endpoints: review detected domain/capture-time, then
generate + download a standardized copy of the HAR with log._analysis
embedded. The one write/export path in the whole app.

Mirrors the original's session-state freeze: /metadata/generate computes
and stashes the standardized bytes on the upload record (instead of
``st.session_state``), and /metadata/download serves exactly that stash --
so the download can never disagree with what "Generate" produced, the same
guarantee the original made.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Response

from app.core.models import embed_analysis, get_embedded_analysis, serialize_har
from app.features.metadata import (
    StandardizeInputs,
    build_standardized_result,
    collect_domain_options,
)
from app.schemas import (
    GenerateMetadataRequest,
    GenerateMetadataResponse,
    HarAnalysisModel,
    MetadataDetected,
    MetadataResponse,
)
from app.shared.naming import derive_metadata_from_entries
from app.store import UploadNotFoundError, UploadRecord, upload_store

router = APIRouter(prefix="/api/har", tags=["metadata"])


def _get_record(upload_id: str) -> UploadRecord:
    try:
        return upload_store.get(upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown upload_id") from exc


@router.get("/{upload_id}/metadata", response_model=MetadataResponse)
async def get_metadata(upload_id: str) -> MetadataResponse:
    """Detected domain/capture time from traffic, plus any existing embedded analysis."""
    record = _get_record(upload_id)

    try:
        derived = derive_metadata_from_entries(record.entries)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    domain_options, first_request_domain = collect_domain_options(
        record.entries, derived.domain, frozenset(derived.other_domains)
    )
    existing = get_embedded_analysis(record.har_data)

    return MetadataResponse(
        detected=MetadataDetected(
            first_request_domain=first_request_domain,
            captured_at=derived.captured_at.isoformat() if derived.captured_at else None,
            domain_options=domain_options,
        ),
        existing_analysis=HarAnalysisModel(**existing.to_dict()) if existing else None,
    )


@router.post("/{upload_id}/metadata/generate", response_model=GenerateMetadataResponse)
async def generate_metadata(
    upload_id: str, body: GenerateMetadataRequest
) -> GenerateMetadataResponse:
    """Build the standardized filename, embed it, and stash the bytes for download."""
    record = _get_record(upload_id)

    if not body.domain.strip():
        raise HTTPException(status_code=400, detail="Domain must not be empty.")

    try:
        captured_at = datetime.fromisoformat(body.captured_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid captured_at: {exc}") from exc

    inputs = StandardizeInputs(
        domain=body.domain,
        interact=body.interact,
        cookies=body.cookies,
        visit=body.visit,
        extra=body.extra,
        captured_at=captured_at,
        description=body.description,
        email_used=body.email_used,
        notes=body.notes,
    )

    try:
        filename, analysis = build_standardized_result(inputs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    updated_har = embed_analysis(record.har_data, analysis)
    upload_store.set_standardized_output(upload_id, filename, serialize_har(updated_har))

    return GenerateMetadataResponse(
        filename=filename, analysis=HarAnalysisModel(**analysis.to_dict())
    )


@router.get("/{upload_id}/metadata/download")
async def download_standardized_har(upload_id: str) -> Response:
    """Serves whatever /metadata/generate last produced for this upload."""
    record = _get_record(upload_id)

    if record.standardized_bytes is None or record.standardized_filename is None:
        raise HTTPException(
            status_code=404, detail="No standardized file generated yet for this upload."
        )

    return Response(
        content=record.standardized_bytes,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{record.standardized_filename}"'},
    )
