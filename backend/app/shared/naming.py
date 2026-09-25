"""Core logic for building standardized HAR test filenames.

Also home to :func:`derive_metadata_from_entries`, which reads the domain
and capture date straight out of a parsed HAR's traffic instead of trusting
a filename or "now". The Metadata endpoint calls :func:`get_har_filename`
below, so the filename format is defined in exactly one place.
"""

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.har_time import parse_started_date_time

if TYPE_CHECKING:
    from app.core.models import ParsedEntry

# Naming variables
PLATFORM_CODES: dict[str, str] = {
    "web": "WEB",
    "mobile": "MOB",
}

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

PLATFORM_LABELS: dict[str, str] = {
    "web": "Web",
    "mobile": "Mobile",
}

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

# Suggested keys for the Metadata form's ground-truth picker. Not exhaustive
# -- the form also accepts a free-typed key.
GROUND_TRUTH_KEY_OPTIONS: list[str] = [
    "E-mail",
    "First Name",
    "Last Name",
    "Username",
    "Phone",
    "IP Address",
    "Date of Birth",
    "Postal Code",
    "Address",
    "Country of Residence",
    "Password",
]


def _labels_by_code(codes: dict[str, str], labels: dict[str, str]) -> dict[str, str]:
    """Invert a key -> code table into the code -> label table filename parsing needs."""
    return {code: labels[key] for key, code in codes.items()}


# Built once at import: the code -> label tables and the filename pattern they
# feed are pure functions of the constants above, so rebuilding and recompiling
# them on every filename parse was wasted work.
_PLATFORM_BY_CODE: dict[str, str] = _labels_by_code(PLATFORM_CODES, PLATFORM_LABELS)
_INTERACT_BY_CODE: dict[str, str] = _labels_by_code(INTERACT_CODES, INTERACT_LABELS)
_COOKIES_BY_CODE: dict[str, str] = _labels_by_code(COOKIES_CODES, COOKIES_LABELS)
_VISIT_BY_CODE: dict[str, str] = _labels_by_code(VISIT_CODES, VISIT_LABELS)

_HAR_NAME_RE = re.compile(
    rf"^(?P<domain>.+)-platform-(?P<platform>{'|'.join(_PLATFORM_BY_CODE)})"
    rf"-interact-(?P<interact>{'|'.join(_INTERACT_BY_CODE)})"
    rf"-cookies-(?P<cookies>{'|'.join(_COOKIES_BY_CODE)})"
    rf"-visit-(?P<visit>{'|'.join(_VISIT_BY_CODE)})"
    r"-extra-(?P<extra>[A-Za-z0-9]{3})"
    r"-(?P<yy>\d{2})-(?P<mm>\d{2})-(?P<dd>\d{2})-(?P<hh>\d{2})\.har$"
)


def normalize_extra_code(extra: str) -> str:
    """Normalize the optional "extra context" field into the fixed 3-char
    code the filename format uses and :func:`get_attrs_from_har_name`'s
    parser requires exactly -- padded, not just truncated, so a 1-2
    character value still round-trips instead of producing a filename the
    parser can't read back (its pattern requires exactly 3 alnum chars)."""
    extra_clean = extra.strip()
    if not extra_clean:
        return "000"
    return extra_clean.upper()[:3].ljust(3, "0")


@dataclass(frozen=True, slots=True)
class DerivedHarMetadata:
    """Domain/date facts read directly from a HAR's own traffic."""

    domain: str
    other_domains: list[str]
    captured_at: datetime | None
    entry_count: int


def _code_for(field_name: str, value: str, codes: dict[str, str]) -> str:
    """The filename code for one naming field's value, or a ValueError naming
    every option that would have been accepted."""
    key = value.strip().lower()
    if key not in codes:
        valid = ", ".join(sorted(codes))
        raise ValueError(f"Invalid {field_name} '{value}'. Valid options: {valid}")
    return codes[key]


def get_har_filename(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    domain: str,
    platform: str,
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

    platform_code = _code_for("platform", platform, PLATFORM_CODES)
    interact_code = _code_for("interact", interact, INTERACT_CODES)
    cookies_code = _code_for("cookies", cookies, COOKIES_CODES)
    # An omitted/blank visit is the documented default, not an invalid value.
    visit_code = _code_for("visit", visit.strip() or DEFAULT_VISIT, VISIT_CODES)

    timestamp = (now or datetime.now()).strftime("%y-%m-%d-%H")

    return (
        f"{domain_clean}-platform-{platform_code}"
        f"-interact-{interact_code}"
        f"-cookies-{cookies_code}"
        f"-visit-{visit_code}"
        f"-extra-{normalize_extra_code(extra)}"
        f"-{timestamp}.har"
    )


def get_attrs_from_har_name(filename: str) -> dict[str, str] | None:
    """Parses a standardized HAR filename and returns human-readable attributes.

    Returns None if the filename doesn't match the structural pattern.
    """
    match = _HAR_NAME_RE.match(filename)
    if not match:
        return None

    # The pattern only admits known codes, so every lookup below is a hit.
    data = match.groupdict()

    return {
        "domain": data["domain"],
        "platform": _PLATFORM_BY_CODE[data["platform"]],
        "interaction": _INTERACT_BY_CODE[data["interact"]],
        "cookies": _COOKIES_BY_CODE[data["cookies"]],
        "visit": _VISIT_BY_CODE[data["visit"]],
        "extra": data["extra"].upper(),
        "timestamp": f"20{data['yy']}-{data['mm']}-{data['dd']} @ {data['hh']}:00",
    }


def derive_metadata_from_entries(entries: "list[ParsedEntry]") -> DerivedHarMetadata:
    """Derive the primary domain and earliest capture time from real traffic.

    The primary domain is whichever domain appears most often across
    entries (typically the site under test, as opposed to third-party/CDN
    domains that show up once or twice). Any other distinct domains seen
    are returned too, so the UI can flag a capture that touched multiple
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
        for parsed in (parse_started_date_time(e.started_date_time) for e in entries)
        if parsed is not None
    ]
    captured_at = min(parsed_dates) if parsed_dates else None

    return DerivedHarMetadata(
        domain=primary_domain,
        other_domains=other_domains,
        captured_at=captured_at,
        entry_count=len(entries),
    )
