"""In-memory store for uploaded HAR files.

This is a local, single-user tool (no auth, no multi-tenant concerns), so a
plain process-lifetime dict keyed by an opaque upload id replaces Streamlit's
``st.session_state``: each upload is parsed once, kept in memory, and looked
up by id on every subsequent request instead of being re-uploaded or
re-parsed per view.
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.core.models import ParsedEntry, build_entries_from_har_data


class UploadNotFoundError(KeyError):
    """Raised when an upload id doesn't exist (never uploaded, or evicted)."""


@dataclass
class UploadRecord:
    """Everything derived from one uploaded HAR file.

    ``har_data`` stays the pristine parsed upload for the record's whole
    lifetime -- it's never mutated in place, matching the original's
    ``load_raw_har(file_bytes)`` always re-reading the untouched original
    bytes. A Metadata "Generate standardized file" call produces a
    *separate* embed_analysis'd copy, stashed in ``standardized_bytes``/
    ``standardized_filename`` for the download endpoint -- the same role
    Streamlit's ``st.session_state`` played for freezing what the download
    button serves.
    """

    upload_id: str
    filename: str
    har_data: dict[str, Any]
    entries: list[ParsedEntry]
    uploaded_at: float = field(default_factory=time.monotonic)
    standardized_bytes: bytes | None = None
    standardized_filename: str | None = None


class UploadStore:
    """Thread-safe in-memory upload registry."""

    def __init__(self) -> None:
        self._records: dict[str, UploadRecord] = {}
        self._lock = Lock()

    def add(self, filename: str, file_bytes: bytes) -> UploadRecord:
        """Parse ``file_bytes`` once and register it under a fresh upload id."""
        har_data = json.loads(file_bytes)
        entries = build_entries_from_har_data(har_data)
        record = UploadRecord(
            upload_id=str(uuid.uuid4()),
            filename=filename,
            har_data=har_data,
            entries=entries,
        )
        with self._lock:
            self._records[record.upload_id] = record
        return record

    def get(self, upload_id: str) -> UploadRecord:
        """Look up a previously uploaded HAR by id, or raise if unknown."""
        with self._lock:
            record = self._records.get(upload_id)
        if record is None:
            raise UploadNotFoundError(upload_id)
        return record

    def set_standardized_output(self, upload_id: str, filename: str, data: bytes) -> UploadRecord:
        """Stash a freshly generated standardized HAR for the download endpoint."""
        with self._lock:
            record = self._records.get(upload_id)
            if record is None:
                raise UploadNotFoundError(upload_id)
            record.standardized_filename = filename
            record.standardized_bytes = data
        return record


# One store per process. A local, single-user analysis tool has no need for
# a shared cache (Redis, etc.) or persistence across restarts.
upload_store = UploadStore()
