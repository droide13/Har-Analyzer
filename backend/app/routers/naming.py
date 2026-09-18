"""Serves the filename-convention label tables from app.shared.naming, so
the frontend's Metadata form never hardcodes a copy that could drift from
the one place the convention is actually defined."""

from fastapi import APIRouter

from app.schemas import NamingOptions
from app.shared.naming import COOKIES_LABELS, INTERACT_LABELS, VISIT_LABELS

router = APIRouter(prefix="/api/naming", tags=["naming"])


@router.get("/options", response_model=NamingOptions)
async def get_naming_options() -> NamingOptions:
    return NamingOptions(interact=INTERACT_LABELS, cookies=COOKIES_LABELS, visit=VISIT_LABELS)
