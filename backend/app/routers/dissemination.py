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
from app.core.models import ParsedEntry, get_embedded_analysis
from app.features.dissemination import (
    Occurrence,
    aggregate_by_domain,
    build_initiator_chain,
    collect_occurrences,
    distinct_values,
    find_dissemination,
    key_options,
    value_timeline,
)
from app.schemas import (
    BadgeFieldMatch,
    DisseminationFirstSeen,
    DisseminationSearchRequest,
    DisseminationSearchResponse,
    DisseminationTimelineResponse,
    EntryBadge,
    EntrySummary,
    InitiatorChainLink,
)
from app.shared.entry_summary import build_entry_summary
from app.shared.search import (
    MatchReason,
    dissemination_badge_labels,
    entry_matches,
    ground_truth_reasons_by_entry,
    reason_field_matches,
    reason_summary_line,
)

from ._common import get_record_or_404

router = APIRouter(prefix="/api/har", tags=["dissemination"])


def _occurrences_or_404(entries: list[ParsedEntry], key: str) -> list[Occurrence]:
    """Every sighting of one key, or the 404 both key-scoped endpoints need."""
    occurrences = collect_occurrences(entries).get(key)
    if not occurrences:
        raise HTTPException(status_code=404, detail="Unknown or unseen key")
    return occurrences


def _badges(reasons: list[MatchReason]) -> list[EntryBadge]:
    """Dissemination has no filter/highlight duality -- every badge is just
    "what matched", so all get the same tone."""
    field_matches = {m.field_label: m for m in reason_field_matches(reasons)}
    badges = []
    for label in dissemination_badge_labels(reasons):
        match = field_matches.get(label)
        matches = [BadgeFieldMatch(attr=match.attr, label=match.field_label, text=match.text)] if match else []
        badges.append(EntryBadge(label=label, tone="orange", matches=matches))
    return badges


def _ground_truth_badges(gt_matches: list[tuple[str, list[MatchReason]]]) -> list[EntryBadge]:
    """One badge per matched ground-truth key -- see
    app.shared.search.ground_truth_reasons_by_entry."""
    return [
        EntryBadge(
            label=f"{key} match: {reason_summary_line(reasons)}",
            tone="error",
            matches=[BadgeFieldMatch(attr=m.attr, label=m.label, text=m.text) for m in reason_field_matches(reasons)],
        )
        for key, reasons in gt_matches
    ]


@router.get("/{upload_id}/dissemination/keys", response_model=list[str])
async def get_dissemination_keys(upload_id: str) -> list[str]:
    """Key names sorted by sighting count, for the "Key to trace" picker."""
    record = get_record_or_404(upload_id)

    return key_options(collect_occurrences(record.entries))


@router.get("/{upload_id}/dissemination/timeline", response_model=DisseminationTimelineResponse)
async def get_dissemination_timeline(
    upload_id: str, key: str = Query(...)
) -> DisseminationTimelineResponse:
    """Sighting count + value-over-time timeline for one key. Always live --
    shown as soon as a key is picked, no scan of the rest of the HAR."""
    record = get_record_or_404(upload_id)
    occurrences = _occurrences_or_404(record.entries, key)

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
    record = get_record_or_404(upload_id)
    occurrences = _occurrences_or_404(record.entries, body.key)

    matches = find_dissemination(record.entries, distinct_values(occurrences), set(body.encodings))

    # By-domain reflects the full (unnarrowed) scan; narrow/highlight only
    # affect the "Matching Entries" list below, matching the original.
    by_domain = aggregate_by_domain(matches)

    narrow_active = bool(body.narrow.strip())
    visible = (
        [(e, r) for e, r in matches if entry_matches(e, body.narrow, "any", set()).matched]
        if narrow_active
        else matches
    )

    # Ground truth check mirrors Network Log's: an opt-in full scan (None
    # means "don't run it"), one badge per matched key, same tone/label
    # convention -- see app.shared.search.ground_truth_reasons_by_entry.
    gt_reasons_by_index: dict[int, list[tuple[str, list[MatchReason]]]] = {}
    if body.gt_keys is not None:
        existing_analysis = get_embedded_analysis(record.har_data)
        if existing_analysis is not None:
            gt_reasons_by_index = ground_truth_reasons_by_entry(
                [e for e, _ in visible], existing_analysis.ground_truth, set(body.gt_keys), set(body.encodings)
            )

    highlight_active = bool(body.highlight.strip())
    rows: list[EntrySummary] = []
    for entry, reasons in visible:
        summary = build_entry_summary(entry)
        summary.badges = _badges(reasons)
        if highlight_active:
            highlight_result = entry_matches(entry, body.highlight, "any", set())
            summary.highlighted = highlight_result.matched
            if highlight_result.matched:
                # The highlight query's own reasons are the more specific "why".
                summary.badges = _badges(highlight_result.reasons)
        gt_matches = gt_reasons_by_index.get(entry.index)
        if gt_matches:
            summary.highlighted = True
            summary.badges = [*summary.badges, *_ground_truth_badges(gt_matches)]
        rows.append(summary)

    return DisseminationSearchResponse(by_domain=by_domain, matches=rows)
