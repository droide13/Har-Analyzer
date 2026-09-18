"""Shared parsing for HAR's ISO-8601 UTC timestamps.

Kept dependency-free (stdlib only) so it can be imported by pure-logic
modules that deliberately avoid pulling in web-framework concerns (e.g.
app/shared/naming.py), as well as by app/core/models.py.
"""

from datetime import datetime


def parse_started_date_time(value: str) -> datetime | None:
    """Parse a HAR ISO-8601 UTC timestamp (e.g. an entry's ``startedDateTime``
    or an embedded ``captured_at``) into a datetime.

    Returns ``None`` on anything unparseable, so one malformed value can't
    blow up a caller processing many.
    """
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def format_started_date_time(value: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """A HAR ISO-8601 UTC timestamp, formatted in the viewer's local time.

    Falls back to the raw value unchanged if it can't be parsed.
    """
    parsed = parse_started_date_time(value)
    return parsed.astimezone().strftime(fmt) if parsed else value
