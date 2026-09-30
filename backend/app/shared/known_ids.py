"""Identifier-name -> known-vendor lookup, built from the studied vendors'
research JSONs under backend/app/data/known_ids/ (see
backend/scripts/sync_tracker_data.py for how that directory is populated).

Deliberately separate from app.shared.trackers: that module classifies a
*domain*; this one matches the literal *name* of a cookie, query param, or
JSON body field (e.g. "id5id" -> ["ID5"]) against each vendor's documented
IDs list. A name can legitimately belong to more than one vendor -- e.g.
"__tamLIResolveResult" is documented by both Live Intent and Open X in the
real data, presumably shared resolution infrastructure rather than a data
error -- so this returns every matching vendor, not just one.
"""

import json
from pathlib import Path

from app.shared.data_files import APP_DATA_DIR

DEFAULT_KNOWN_IDS_DIR = APP_DATA_DIR / "known_ids"

# A studied vendor whose research hasn't been filled in yet ships this
# literal placeholder as its only "ID" (see e.g. appnexus.json/gumgum.json)
# -- never a real cookie/param/field name, so it must never be treated as
# one. (The empty-string case is already caught by the `not name` check
# where this set is used, so it doesn't need to be listed here too.)
_PLACEHOLDER_ID_NAMES = {"<id>"}

KnownIdsTable = dict[str, list[str]]


def load_known_ids(directory: Path = DEFAULT_KNOWN_IDS_DIR) -> KnownIdsTable:
    """id-name -> the list of vendor Service names that document it.
    Missing directory (e.g. before the sync script has ever run) just means
    nothing matches, not an error."""
    table: KnownIdsTable = {}
    if not directory.is_dir():
        return table

    for json_path in sorted(directory.glob("*.json")):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        research = data.get("research", {})
        service = str(research.get("Service") or json_path.stem)
        for entry in research.get("IDs", []):
            name = str(entry.get("ID") or "").strip()
            if not name or name.lower() in _PLACEHOLDER_ID_NAMES:
                continue
            vendors = table.setdefault(name, [])
            if service not in vendors:
                vendors.append(service)
    return table


# Loaded once at import -- static reference data, not per-upload state.
_KNOWN_IDS: KnownIdsTable = load_known_ids()


def vendor_for_id_name(name: str, table: KnownIdsTable | None = None) -> list[str]:
    """Every studied vendor that documents this exact identifier name (an
    exact, case-sensitive match -- a cookie/param name's casing is part of
    its identity, not incidental), or an empty list if none do. ``table``
    is injectable for tests; omit it to use the real data loaded at import.

    Always a fresh list, never the table's own stored list -- so a caller
    that appends to what it gets back (e.g. merging in a manually-detected
    vendor) can't mutate the shared, cached table out from under every
    future lookup of the same name."""
    known_ids = _KNOWN_IDS if table is None else table
    return list(known_ids.get(name, []))
