"""Dissemination tab endpoints: trace one query-param/cookie key's value(s)
across the whole capture.

Two different cost profiles, matching the original's split between a
fragment that re-runs live and a form that only submits on demand:
- ``keys``/``timeline`` are cheap (group-by-name over already-parsed
  entries) and safe to call on every key selection.
- ``search`` runs ``find_dissemination`` -- a full scan of every entry for
  every distinct value -- so the frontend only calls it on an explicit
  "Search dissemination" click or a narrow/highlight edit after that,
  never automatically alongside ``timeline``.
"""

from fastapi import APIRouter, HTTPException, Query

from app.core.har_time import format_started_date_time
from app.features.dissemination import (
    aggregate_by_domain,
    build_initiator_chain,
    collect_occurrences,
    distinct_values,
    find_dissemination,
    key_options,
    reason_summary,
    value_timeline,
)
from app.schemas import (
    DisseminationFirstSeen,
    DisseminationMatchRow,
    DisseminationSearchRequest,
    DisseminationSearchResponse,
    DisseminationTimelineResponse,
    InitiatorChainLink,
)
from app.shared.entry_summary import build_entry_summary
from app.shared.search import dissemination_badge_labels, entry_matches
from app.store import UploadNotFoundError, upload_store

router = APIRouter(prefix="/api/har", tags=["dissemination"])


@router.get("/{upload_id}/dissemination/keys", response_model=list[str])
async def get_dissemination_keys(upload_id: str) -> list[str]:
    """Key names sorted by sighting count, for the "Key to trace" picker."""
    try:
        record = upload_store.get(upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown upload_id") from exc

    return key_options(collect_occurrences(record.entries))


@router.get("/{upload_id}/dissemination/timeline", response_model=DisseminationTimelineResponse)
async def get_dissemination_timeline(
    upload_id: str, key: str = Query(...)
) -> DisseminationTimelineResponse:
    """Sighting count + value-over-time timeline for one key. Always live --
    shown as soon as a key is picked, no scan of the rest of the HAR."""
    try:
        record = upload_store.get(upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown upload_id") from exc

    registry = collect_occurrences(record.entries)
    occurrences = registry.get(key)
    if not occurrences:
        raise HTTPException(status_code=404, detail="Unknown or unseen key")

    first_entry, first_origin, first_value = occurrences[0]
    when = (
        format_started_date_time(first_entry.started_date_time)
        if first_entry.started_date_time
        else f"entry #{first_entry.index} (no timestamp)"
    )

    initiator_chain = [
        InitiatorChainLink(
            found=hop.found,
            entry=build_entry_summary(hop.entry) if hop.entry is not None else None,
            url=hop.url,
            initiator_type=hop.initiator_type,
        )
        for hop in build_initiator_chain(record.entries, first_entry)
    ]

    return DisseminationTimelineResponse(
        sightings=len(occurrences),
        distinct_values=len(distinct_values(occurrences)),
        origins=sorted({occ[1] for occ in occurrences}),
        first_seen=DisseminationFirstSeen(
            origin=first_origin,
            when=when,
            method=first_entry.method,
            domain=first_entry.domain,
            value=first_value or "(empty)",
        ),
        initiator_chain=initiator_chain,
        timeline=value_timeline(occurrences),
    )


@router.post("/{upload_id}/dissemination/search", response_model=DisseminationSearchResponse)
async def post_dissemination_search(
    upload_id: str, body: DisseminationSearchRequest
) -> DisseminationSearchResponse:
    """Full dissemination scan for one key's values, optionally narrowed/highlighted."""
    try:
        record = upload_store.get(upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown upload_id") from exc

    registry = collect_occurrences(record.entries)
    occurrences = registry.get(body.key)
    if not occurrences:
        raise HTTPException(status_code=404, detail="Unknown or unseen key")

    values = distinct_values(occurrences)
    encodings = set(body.encodings)
    matches = find_dissemination(record.entries, values, encodings)

    # By-domain reflects the full (unnarrowed) scan; narrow/highlight only
    # affect the "Matching Entries" list below, matching the original.
    by_domain = aggregate_by_domain(matches)

    narrow_active = bool(body.narrow.strip())
    visible = (
        [(e, r) for e, r in matches if entry_matches(e, body.narrow, "any", set()).matched]
        if narrow_active
        else matches
    )

    highlight_active = bool(body.highlight.strip())
    rows: list[DisseminationMatchRow] = []
    for entry, reasons in visible:
        summary = build_entry_summary(entry)
        badges = dissemination_badge_labels(reasons)
        if highlight_active:
            highlight_result = entry_matches(entry, body.highlight, "any", set())
            summary.highlighted = highlight_result.matched
            if highlight_result.matched:
                badges = dissemination_badge_labels(highlight_result.reasons)
        summary.badges = badges
        rows.append(DisseminationMatchRow(entry=summary, reasons=reason_summary(reasons)))

    return DisseminationSearchResponse(by_domain=by_domain, matches=rows)
