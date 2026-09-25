"""Core logic for standardizing an existing HAR file and tagging it with
experiment metadata (``log._analysis``). Pure functions of their arguments
throughout.

Staleness detection (whether the form has changed since the last generated
download) is a plain client-side object comparison instead -- see
frontend/src/features/metadata -- no backend round trip needed for it.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from urllib.parse import urlparse

from app.core.models import GroundTruthEntry, HarAnalysis, ParsedEntry
from app.shared.naming import get_har_filename, normalize_extra_code

_CUSTOM_DOMAIN_LABEL = "Custom domain..."


@dataclass(frozen=True, slots=True)
class StandardizeInputs:  # pylint: disable=too-many-instance-attributes
    """User-confirmed values needed to standardize and tag one HAR file."""

    # Mirrors HarAnalysis's fields on purpose: this is the raw form input,
    # HarAnalysis is the validated record built from it.
    domain: str
    platform: str
    interact: str
    cookies: str
    visit: str
    extra: str
    captured_at: datetime
    description: str = ""
    ground_truth: tuple[GroundTruthEntry, ...] = ()
    notes: str = ""


def build_standardized_result(inputs: StandardizeInputs) -> tuple[str, HarAnalysis]:
    """Build the standardized filename and the HarAnalysis record to embed.

    Raises ``ValueError`` (propagated from :func:`get_har_filename`) if the
    domain/interact/cookies/visit combination is invalid.
    """
    filename = get_har_filename(
        domain=inputs.domain,
        platform=inputs.platform,
        interact=inputs.interact,
        cookies=inputs.cookies,
        visit=inputs.visit,
        extra=inputs.extra,
        now=inputs.captured_at,
    )

    # Drop rows the user started but never filled in (either side blank) --
    # a half-entered key/value pair isn't ground truth worth embedding.
    ground_truth = tuple(
        GroundTruthEntry(key=g.key.strip(), value=g.value.strip())
        for g in inputs.ground_truth
        if g.key.strip() and g.value.strip()
    )

    analysis = HarAnalysis(
        domain=inputs.domain.strip(),
        platform=inputs.platform.strip().lower(),
        interact=inputs.interact.strip().lower(),
        cookies=inputs.cookies.strip().lower(),
        visit=inputs.visit.strip().lower(),
        extra=normalize_extra_code(inputs.extra),
        captured_at=inputs.captured_at.isoformat(),
        standardized_filename=filename,
        description=inputs.description.strip(),
        ground_truth=ground_truth,
        notes=inputs.notes.strip(),
    )
    return filename, analysis


def extract_entry_domain(entry: Any) -> str | None:
    """Pull the domain/host out of an entry, whether it's a ParsedEntry or a plain dict."""
    domain_val = cast(object, getattr(entry, "domain", None))
    if isinstance(domain_val, str) and domain_val.strip():
        return domain_val.strip().lower()

    url_val = cast(object, getattr(entry, "url", None))
    if url_val is None and isinstance(entry, dict) and "url" in entry:
        url_val = cast(object, entry["url"])

    if isinstance(url_val, str) and url_val.strip():
        parsed = urlparse(url_val)
        netloc = parsed.netloc or parsed.path.split("/")[0]
        host = netloc.split(":")[0].strip().lower()
        if host:
            return host

    return None


def collect_domain_options(
    entries: list[ParsedEntry], derived_domain: str, other_domains: frozenset[str]
) -> tuple[list[str], str]:
    """Build the dropdown's option list and return it alongside the first-seen domain.

    Order: first request's domain, then every other domain seen in traffic order,
    then the analyzer's own "primary" guess, then any other domains it flagged,
    then a trailing "Custom domain..." sentinel for the UI to special-case.
    """
    ordered_domains: list[str] = []
    for entry in entries:
        dom = extract_entry_domain(entry)
        if dom and dom not in ordered_domains:
            ordered_domains.append(dom)

    first_request_domain = ordered_domains[0] if ordered_domains else derived_domain

    options: list[str] = []
    for dom in (first_request_domain, *ordered_domains, derived_domain, *sorted(other_domains)):
        if dom and dom not in options:
            options.append(dom)
    options.append(_CUSTOM_DOMAIN_LABEL)

    return options, first_request_domain


def is_custom_domain_choice(choice: str) -> bool:
    """Whether the dropdown's sentinel "type your own" option was picked."""
    return choice == _CUSTOM_DOMAIN_LABEL


def analysis_table_rows(analysis: HarAnalysis) -> list[dict[str, str]]:
    """Turn a HarAnalysis into Field/Value rows a table widget can render directly."""
    return [
        {"Field": field.replace("_", " ").title(), "Value": str(value)}
        for field, value in analysis.to_dict().items()
    ]
