"""Parsing and flattening for HAR entries' JSON request/response bodies.

Generic on purpose -- not tied to identifier detection specifically, since
any feature that wants to look inside a JSON payload (an identifier hiding
in a body field today; a Dissemination trace across body-derived keys,
potentially, tomorrow) needs the exact same two steps: confirm a body is
actually JSON, then walk it into flat (path, value) pairs.
"""

import json
from typing import Any


def parse_json_body(body: str) -> Any | None:
    """Parse a HAR entry's request/response body as JSON, or None if it
    isn't one. Most bodies are HTML/JS/binary/form-encoded, so a cheap
    first-character check skips the doomed json.loads attempt (and its
    exception) for the common non-JSON case instead of paying for it on
    every entry."""
    text = body.strip()
    if not text or text[0] not in "{[":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def flatten_json(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Recursively flatten a parsed JSON value into (dotted-path, string
    value) pairs for every leaf -- e.g. ``{"fms_params": {"fms_uid2":
    "A4..."}}`` becomes ``[("fms_params.fms_uid2", "A4...")]``. This is what
    lets an identifier a site hands back inside a JSON payload (a UID2
    token, an email hash, a resolved third-party ID) be found at all,
    instead of being invisible just because it never appears in a cookie or
    query param."""
    if isinstance(value, dict):
        pairs: list[tuple[str, str]] = []
        for key, sub_value in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            pairs.extend(flatten_json(sub_value, path))
        return pairs
    if isinstance(value, list):
        pairs = []
        for i, sub_value in enumerate(value):
            pairs.extend(flatten_json(sub_value, f"{prefix}[{i}]"))
        return pairs
    if value is None:
        return []
    return [(prefix, str(value))]
