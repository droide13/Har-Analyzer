"""Identifiers tab endpoint: stable-identifier detection over query params
and cookies, with the same 4-signal filters as the original (appearance
count, value cardinality, average length, entropy) plus a name search and
noise-key exclusion."""

from typing import Callable, Literal

from fastapi import APIRouter, Query

from app.core.models import ParsedEntry
from app.features.identifiers import (
    Item,
    TrackedKey,
    extract_tracked_keys,
    filter_identifiers,
    get_cookie_items,
    get_query_items,
    sort_identifiers,
)
from app.schemas import IdentifiersResponse, IdentifierSummaryRow, IdentifierValueRow

from ._common import get_record_or_404

router = APIRouter(prefix="/api/har", tags=["identifiers"])

SortBy = Literal["Appearances", "Entropy", "Avg length", "Unique values"]


def _to_summary_row(tk: TrackedKey) -> IdentifierSummaryRow:
    values = sorted(tk.values.values(), key=lambda v: v.appearances, reverse=True)
    return IdentifierSummaryRow(
        key=tk.key,
        first_seen_as=tk.first_seen_as,
        appearances=tk.total_appearances,
        unique_values=tk.unique_value_count,
        avg_length=round(tk.avg_length, 1),
        avg_entropy=round(tk.avg_entropy, 2),
        domains=", ".join(sorted(tk.all_domains)),
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
    entries: list[ParsedEntry],
    get_items: Callable[[ParsedEntry], list[Item]],
    filters: dict[str, object],
    sort_by: str,
) -> list[IdentifierSummaryRow]:
    tracked = extract_tracked_keys(entries, get_items)
    identifiers = sort_identifiers(filter_identifiers(tracked, **filters), sort_by)
    return [_to_summary_row(tk) for tk in identifiers]


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

    return IdentifiersResponse(
        query_params=_build_section(record.entries, get_query_items, filters, sort_by),
        cookies=_build_section(record.entries, get_cookie_items, filters, sort_by),
    )
