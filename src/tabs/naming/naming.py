"""Core logic for building standardized HAR test filenames.

Also home to :func:`derive_metadata_from_entries`, which reads the domain
and capture date straight out of a parsed HAR's traffic instead of trusting
a filename or "now". The post-capture standardizer (``tabs/metadata``) calls
:func:`get_har_filename` below, so the filename format is defined in exactly
one place.
"""

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import ParsedEntry

# Naming variables
INTERACT_CODES: dict[str, str] = {
    "load": "LOA",
    "navigate": "NAV",
    "enter_email": "EMA",
    "sign_up": "SIG",
    "login": "LOG",
}

COOKIES_CODES: dict[str, str] = {
    "accept": "ACC",
    "deny": "DEN",
    "ignore": "IGN",
}

VISIT_CODES: dict[str, str] = {
    "first": "FIR",
    "second": "SEC",
    "delete": "DEL",
}

DEFAULT_VISIT: str = "first"

INTERACT_LABELS: dict[str, str] = {
    "load": "Load page",
    "navigate": "Navigate",
    "enter_email": "Enter email",
    "sign_up": "Sign up",
    "login": "Login",
}

COOKIES_LABELS: dict[str, str] = {
    "accept": "Accept",
    "deny": "Deny",
    "ignore": "Ignore",
}

VISIT_LABELS: dict[str, str] = {
    "first": "First visit (fresh state)",
    "second": "Second visit (reuse existing cookies/state)",
    "delete": "Delete cookies & reload (regenerate from scratch)",
}


@dataclass(frozen=True, slots=True)
class DerivedHarMetadata:
    """Domain/date facts read directly from a HAR's own traffic."""

    domain: str
    other_domains: list[str]
    captured_at: datetime | None
    entry_count: int


def get_har_filename(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    domain: str,
    interact: str,
    cookies: str,
    visit: str = DEFAULT_VISIT,
    extra: str = "",
    now: datetime | None = None,
) -> str:
    """Build the .har filename for a given test scenario.

    ``now`` defaults to the current time (the pre-capture "generate a name
    to save under" flow), but callers standardizing an existing capture
    should pass the HAR's own derived timestamp instead -- see
    :func:`derive_metadata_from_entries`.
    """
    domain_clean = domain.strip()
    if not domain_clean:
        raise ValueError("Domain must not be empty.")

    interact_key = interact.strip().lower()
    cookies_key = cookies.strip().lower()
    visit_key = visit.strip().lower() if visit.strip() else DEFAULT_VISIT

    if interact_key not in INTERACT_CODES:
        valid = ", ".join(sorted(INTERACT_CODES))
        raise ValueError(f"Invalid interact '{interact}'. Valid options: {valid}")
    if cookies_key not in COOKIES_CODES:
        valid = ", ".join(sorted(COOKIES_CODES))
        raise ValueError(f"Invalid cookies '{cookies}'. Valid options: {valid}")
    if visit_key not in VISIT_CODES:
        valid = ", ".join(sorted(VISIT_CODES))
        raise ValueError(f"Invalid visit '{visit}'. Valid options: {valid}")

    extra_code = extra.strip().upper()[:3] if extra.strip() else "000"
    timestamp = (now or datetime.now()).strftime("%y-%m-%d-%H")

    return (
        f"{domain_clean}-interact-{INTERACT_CODES[interact_key]}"
        f"-cookies-{COOKIES_CODES[cookies_key]}"
        f"-visit-{VISIT_CODES[visit_key]}"
        f"-extra-{extra_code}"
        f"-{timestamp}.har"
    )


def get_attrs_from_har_name(filename: str) -> dict[str, str] | None:
    """Parses a standardized HAR filename and returns human-readable attributes.

    Returns None if the filename doesn't match the structural pattern.
    """
    interact_map = {code: INTERACT_LABELS[key] for key, code in INTERACT_CODES.items()}
    cookies_map = {code: COOKIES_LABELS[key] for key, code in COOKIES_CODES.items()}
    visit_map = {code: VISIT_LABELS[key] for key, code in VISIT_CODES.items()}

    interact_pattern = "|".join(interact_map.keys())
    cookies_pattern = "|".join(cookies_map.keys())
    visit_pattern = "|".join(visit_map.keys())

    pattern = (
        rf"^(?P<domain>.+)-interact-(?P<interact>{interact_pattern})"
        rf"-cookies-(?P<cookies>{cookies_pattern})"
        rf"-visit-(?P<visit>{visit_pattern})"
        r"-extra-(?P<extra>[A-Za-z0-9]{3})"
        r"-(?P<yy>\d{2})-(?P<mm>\d{2})-(?P<dd>\d{2})-(?P<hh>\d{2})\.har$"
    )

    match = re.match(pattern, filename)
    if not match:
        return None

    data = match.groupdict()

    return {
        "domain": data["domain"],
        "interaction": interact_map.get(data["interact"], data["interact"]),
        "cookies": cookies_map.get(data["cookies"], data["cookies"]),
        "visit": visit_map.get(data["visit"], data["visit"]),
        "extra": data["extra"].upper(),
        "timestamp": f"20{data['yy']}-{data['mm']}-{data['dd']} @ {data['hh']}:00",
    }


def _parse_started_date_time(value: str) -> datetime | None:
    """Parse a HAR entry's ISO-8601 ``startedDateTime`` into a datetime.

    Returns ``None`` (rather than raising) on anything unparseable, so one
    malformed entry can't blow up metadata derivation for the whole file.
    """
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def derive_metadata_from_entries(entries: "list[ParsedEntry]") -> DerivedHarMetadata:
    """Derive the primary domain and earliest capture time from real traffic.

    The primary domain is whichever domain appears most often across
    entries (typically the site under test, as opposed to third-party/CDN
    domains that show up once or twice). Any other distinct domains seen
    are returned too, so the UI can flag capture that touched multiple
    sites and let the user confirm which one is "the" domain.
    """
    if not entries:
        raise ValueError("Cannot derive metadata from an empty entry list.")

    domain_counts = Counter(e.domain for e in entries if e.domain and e.domain != "unknown")
    if not domain_counts:
        raise ValueError("No usable domain found in this HAR's entries.")

    primary_domain, _ = domain_counts.most_common(1)[0]
    other_domains = sorted(d for d in domain_counts if d != primary_domain)

    parsed_dates = [
        parsed
        for parsed in (_parse_started_date_time(e.started_date_time) for e in entries)
        if parsed is not None
    ]
    captured_at = min(parsed_dates) if parsed_dates else None

    return DerivedHarMetadata(
        domain=primary_domain,
        other_domains=other_domains,
        captured_at=captured_at,
        entry_count=len(entries),
    )
