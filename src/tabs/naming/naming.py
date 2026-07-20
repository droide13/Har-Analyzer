"""Core logic for building standardized HAR test filenames."""

import re
from datetime import datetime

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


def get_har_filename(
    domain: str,
    interact: str,
    cookies: str,
    visit: str = DEFAULT_VISIT,
    extra: str = "",
    now: datetime | None = None,
) -> str:
    """Build the .har filename for a given test scenario."""
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
    # Rebuilt mapping structures to explicitly satisfy C0206 via .items()
    interact_map = {
        code: INTERACT_LABELS[key] for key, code in INTERACT_CODES.items()
    }
    cookies_map = {
        code: COOKIES_LABELS[key] for key, code in COOKIES_CODES.items()
    }
    visit_map = {
        code: VISIT_LABELS[key] for key, code in VISIT_CODES.items()
    }

    interact_pattern = "|".join(interact_map.keys())
    cookies_pattern = "|".join(cookies_map.keys())
    visit_pattern = "|".join(visit_map.keys())

    # Changed rf"" to r"" on the extra block so {3} is treated as regex syntax
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
