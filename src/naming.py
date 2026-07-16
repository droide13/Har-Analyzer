"""Core logic for building standardized HAR test filenames."""

from datetime import datetime

# Maps from internal key -> 3-letter filename code.
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


def get_har_filename(
    domain: str,
    interact: str,
    cookies: str,
    visit: str = DEFAULT_VISIT,
    extra: str = "",
    now: datetime | None = None,
) -> str:
    """Build the .har filename for a given test scenario.

    Raises:
        ValueError: if domain is empty or interact/cookies/visit is unrecognized.
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