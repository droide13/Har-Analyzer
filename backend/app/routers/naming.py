"""Serves the filename-convention label tables from app.shared.naming, so
the frontend's Metadata form never hardcodes a copy that could drift from
the one place the convention is actually defined."""

from fastapi import APIRouter

from app.schemas import NamingOptions
from app.shared.naming import (
    COOKIES_LABELS,
    GROUND_TRUTH_KEY_OPTIONS,
    INTERACT_LABELS,
    PLATFORM_LABELS,
    VISIT_LABELS,
)

router = APIRouter(prefix="/api/naming", tags=["naming"])


@router.get("/options", response_model=NamingOptions)
async def get_naming_options() -> NamingOptions:
    """Platform/interact/cookies/visit code -> label tables for the Metadata form's selects."""
    return NamingOptions(
        platform=PLATFORM_LABELS,
        interact=INTERACT_LABELS,
        cookies=COOKIES_LABELS,
        visit=VISIT_LABELS,
        ground_truth_keys=GROUND_TRUTH_KEY_OPTIONS,
    )
