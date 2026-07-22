"""Core logic for standardizing an existing HAR file and tagging it with
experiment metadata (``log._analysis``).

Deliberately thin: it composes ``core.models.HarAnalysis`` and
``tabs.naming.naming.get_har_filename`` rather than reimplementing either,
so the filename format and the metadata schema each stay defined in one
place.
"""

from dataclasses import dataclass
from datetime import datetime

from core.models import HarAnalysis
from tabs.naming.naming import get_har_filename


@dataclass(frozen=True, slots=True)
class StandardizeInputs:
    """User-confirmed values needed to standardize and tag one HAR file."""

    domain: str
    interact: str
    cookies: str
    visit: str
    extra: str
    captured_at: datetime
    description: str = ""
    email_used: str = ""
    notes: str = ""


def build_standardized_result(inputs: StandardizeInputs) -> tuple[str, HarAnalysis]:
    """Build the standardized filename and the HarAnalysis record to embed.

    Raises ``ValueError`` (propagated from :func:`get_har_filename`) if the
    domain/interact/cookies/visit combination is invalid.
    """
    filename = get_har_filename(
        domain=inputs.domain,
        interact=inputs.interact,
        cookies=inputs.cookies,
        visit=inputs.visit,
        extra=inputs.extra,
        now=inputs.captured_at,
    )

    extra_clean = inputs.extra.strip()
    analysis = HarAnalysis(
        domain=inputs.domain.strip(),
        interact=inputs.interact.strip().lower(),
        cookies=inputs.cookies.strip().lower(),
        visit=inputs.visit.strip().lower(),
        extra=extra_clean.upper()[:3] if extra_clean else "000",
        captured_at=inputs.captured_at.isoformat(),
        standardized_filename=filename,
        description=inputs.description.strip(),
        email_used=inputs.email_used.strip(),
        notes=inputs.notes.strip(),
    )
    return filename, analysis
