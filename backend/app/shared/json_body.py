"""Parsing and flattening for HAR entries' JSON request/response bodies.

Generic on purpose -- not tied to identifier detection specifically, since
any feature that wants to look inside a JSON payload (an identifier hiding
in a body field today; a Dissemination trace across body-derived keys,
potentially, tomorrow) needs the exact same two steps: confirm a body is
actually JSON, then walk it into flat (path, value) pairs.
"""

import json
from typing import Any

# A real identifier-bearing payload (an identity sync response, a consent/
# token bundle) is small -- a few KB at most, a few dozen to low hundreds of
# fields. A body past this size is essentially never that; it's a product
# catalog, a config dump, a translations table, a geo/IP list -- exactly the
# shape that turns "flatten this JSON" into tens of thousands of useless
# leaves. Skipping those outright (both the wasted json.loads and the
# flattening) is what keeps a capture with one or two such responses from
# producing a response so large the frontend chokes rendering it.
MAX_BODY_CHARS = 100_000

# A second, independent cap on the *flattened* output, in case a body stays
# under MAX_BODY_CHARS but is still unusually wide/deep (e.g. a compact but
# very long flat array). Stops collecting once this many leaves have been
# found rather than raising -- a body that hits this cap almost certainly
# isn't identifier-bearing either, so a silent partial result is fine.
MAX_LEAVES_PER_BODY = 300


def parse_json_body(body: str) -> Any | None:
    """Parse a HAR entry's request/response body as JSON, or None if it
    isn't one, or is too large to be worth treating as one (see
    MAX_BODY_CHARS). Most bodies are HTML/JS/binary/form-encoded, so a cheap
    first-character check skips the doomed json.loads attempt (and its
    exception) for the common non-JSON case instead of paying for it on
    every entry."""
    text = body.strip()
    if not text or len(text) > MAX_BODY_CHARS or text[0] not in "{[":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def flatten_json(value: Any, prefix: str = "", max_leaves: int = MAX_LEAVES_PER_BODY) -> list[tuple[str, str]]:
    """Recursively flatten a parsed JSON value into (dotted-path, string
    value) pairs for every leaf -- e.g. ``{"fms_params": {"fms_uid2":
    "A4..."}}`` becomes ``[("fms_params.fms_uid2", "A4...")]``. This is what
    lets an identifier a site hands back inside a JSON payload (a UID2
    token, an email hash, a resolved third-party ID) be found at all,
    instead of being invisible just because it never appears in a cookie or
    query param.

    Stops once ``max_leaves`` pairs have been collected -- see
    MAX_LEAVES_PER_BODY."""
    out: list[tuple[str, str]] = []
    _flatten_into(value, prefix, max_leaves, out)
    return out


def _flatten_into(value: Any, prefix: str, max_leaves: int, out: list[tuple[str, str]]) -> None:
    if len(out) >= max_leaves:
        return
    if isinstance(value, dict):
        for key, sub_value in value.items():
            if len(out) >= max_leaves:
                return
            path = f"{prefix}.{key}" if prefix else str(key)
            _flatten_into(sub_value, path, max_leaves, out)
        return
    if isinstance(value, list):
        for i, sub_value in enumerate(value):
            if len(out) >= max_leaves:
                return
            _flatten_into(sub_value, f"{prefix}[{i}]", max_leaves, out)
        return
    if value is None:
        return
    out.append((prefix, str(value)))
