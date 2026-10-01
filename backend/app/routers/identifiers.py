"""Identifiers tab endpoint: stable-identifier detection over query params,
cookies, and JSON request/response body fields, with the same 4-signal
filters as the original (appearance count, value cardinality, average
length, entropy) plus a name search and noise-key exclusion. A fourth
source, Known IDs, bypasses those filters for an exact-name match against
studied vendors' documented identifiers instead -- see
app.features.identifiers' module docstring."""

from typing import Literal

from fastapi import APIRouter, Query

from app.features.identifiers import (
    TrackedKey,
    extract_tracked_keys,
    filter_identifiers,
    filter_known_ids,
    get_all_items,
    get_body_items,
    get_cookie_items,
    get_query_items,
    sort_identifiers,
)
from app.schemas import IdentifiersResponse, IdentifierSummaryRow, IdentifierValueRow
from app.shared.known_ids import vendor_for_id_name

from ._common import get_record_or_404

router = APIRouter(prefix="/api/har", tags=["identifiers"])

SortBy = Literal["Appearances", "Entropy", "Avg length", "Unique values"]


def _to_summary_row(tk: TrackedKey, vendor: str | None = None) -> IdentifierSummaryRow:
    values = sorted(tk.values.values(), key=lambda v: v.appearances, reverse=True)
    return IdentifierSummaryRow(
        key=tk.key,
        first_seen_as=tk.first_seen_as,
        appearances=tk.total_appearances,
        unique_values=tk.unique_value_count,
        avg_length=round(tk.avg_length, 1),
        avg_entropy=round(tk.avg_entropy, 2),
        domains=", ".join(sorted(tk.all_domains)),
        vendor=vendor,
        values=[
            IdentifierValueRow(
                value=v.value,
                first_seen_as=v.first_seen_as,
                appearances=v.appearances,
                length=len(v.value),
                entropy=round(v.entropy, 2),
                domains=", ".join(sorted(v.domains)),
            )
            for v in values
        ],
    )


def _build_section(
    tracked: dict[str, TrackedKey],
    filters: dict[str, object],
    sort_by: str,
) -> list[IdentifierSummaryRow]:
    identifiers = sort_identifiers(filter_identifiers(tracked, **filters), sort_by)
    return [_to_summary_row(tk) for tk in identifiers]


def _build_known_ids_section(
    tracked: dict[str, TrackedKey], name_query: str, sort_by: str
) -> list[IdentifierSummaryRow]:
    identifiers = sort_identifiers(filter_known_ids(tracked, name_query), sort_by)
    return [_to_summary_row(tk, vendor=", ".join(vendor_for_id_name(tk.key))) for tk in identifiers]


@router.get("/{upload_id}/identifiers", response_model=IdentifiersResponse)
async def get_identifiers(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    upload_id: str,
    min_appearances: int = Query(default=20, ge=1, le=200),
    max_unique_values: int = Query(default=5, ge=1, le=20),
    min_avg_length: int = Query(default=20, ge=0, le=64),
    min_avg_entropy: float = Query(default=2.5, ge=0.0, le=6.0),
    name_query: str = Query(default=""),
    exclude_common: bool = Query(default=True),
    sort_by: SortBy = Query(default="Appearances"),
) -> IdentifiersResponse:
    """Query-param and cookie keys matching the 4-signal identifier filters."""
    record = get_record_or_404(upload_id)

    filters = {
        "min_appearances": min_appearances,
        "max_unique_values": max_unique_values,
        "min_avg_length": min_avg_length,
        "min_avg_entropy": min_avg_entropy,
        "name_query": name_query,
        "exclude_common": exclude_common,
    }

    query_tracked = extract_tracked_keys(record.entries, get_query_items)
    cookie_tracked = extract_tracked_keys(record.entries, get_cookie_items)
    body_tracked = extract_tracked_keys(record.entries, get_body_items)

    # Known IDs matches across all three item kinds, so it needs its own
    # pass over entries with get_all_items (rather than combining the three
    # tracked dicts above after the fact) -- that keeps "first seen as"
    # correct by true chronology across sources, which combining
    # already-aggregated per-source dicts can't recover.
    all_tracked = extract_tracked_keys(record.entries, get_all_items)

    return IdentifiersResponse(
        query_params=_build_section(query_tracked, filters, sort_by),
        cookies=_build_section(cookie_tracked, filters, sort_by),
        body_fields=_build_section(body_tracked, filters, sort_by),
        known_ids=_build_known_ids_section(all_tracked, name_query, sort_by),
    )
