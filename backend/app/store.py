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
    """Everything derived from one uploaded HAR file."""

    upload_id: str
    filename: str
    har_data: dict[str, Any]
    entries: list[ParsedEntry]
    uploaded_at: float = field(default_factory=time.monotonic)


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

    def replace_har_data(self, upload_id: str, har_data: dict[str, Any]) -> UploadRecord:
        """Swap in a new ``har_data`` for an existing upload (Metadata's embed step)."""
        with self._lock:
            record = self._records.get(upload_id)
            if record is None:
                raise UploadNotFoundError(upload_id)
            record.har_data = har_data
        return record


# One store per process. A local, single-user analysis tool has no need for
# a shared cache (Redis, etc.) or persistence across restarts.
upload_store = UploadStore()
