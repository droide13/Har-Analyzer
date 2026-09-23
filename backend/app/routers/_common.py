"""Shared helpers for router modules."""

from fastapi import HTTPException

from app.store import UploadNotFoundError, UploadRecord, upload_store


def get_record_or_404(upload_id: str) -> UploadRecord:
    """Look up an upload by id, or raise the 404 every router needs for an unknown one."""
    try:
        return upload_store.get(upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown upload_id") from exc
