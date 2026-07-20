#!/usr/bin/env python3
"""
har_extract.py

Parses a HAR (HTTP Archive) file and extracts:
  1. Query string parameters (name -> distinct values + the requests each
     value showed up in)
  2. Cookies (name -> distinct values + the requests each value showed up
     in, incl. security flags)
  3. POST data (raw body per request that had one)

Usage:
    python har_extract.py input.har output.json

Strictly typed with dataclasses + type hints, designed to be easy to
extend (e.g. add response headers, response cookies, etc.).
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------
# Data structures
# --------------------------------------------------------------------------


@dataclass
class RequestRef:
    """A single request in which a given param/cookie value showed up."""

    connection_id: str
    method: str
    url: str


@dataclass
class CookieRequestRef(RequestRef):
    """Same as RequestRef but with cookie-specific security flags."""

    domain: Optional[str] = None
    path: Optional[str] = None
    http_only: Optional[bool] = None
    secure: Optional[bool] = None
    same_site: Optional[str] = None
    expires: Optional[str] = None


@dataclass
class ValueOccurrence:
    """One distinct value seen for a param/cookie, and where it showed up."""

    value: str
    appearances: int = 0
    requests: List[RequestRef] = field(default_factory=list[RequestRef])


@dataclass
class TrackedValue:
    """Aggregated info for one param/cookie name across the whole HAR."""

    key: str
    appearances: int = 0
    values: List[ValueOccurrence] = field(default_factory=list[ValueOccurrence])


@dataclass
class PostDataEntry:
    connection_id: str
    url: str
    method: str
    mime_type: Optional[str]
    post_data: str


# --------------------------------------------------------------------------
# Core extraction logic
# --------------------------------------------------------------------------


def load_har(path: str) -> Dict[str, Any]:
    """Load and return the raw HAR JSON structure."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_or_create_value(values: List[ValueOccurrence], value: str) -> ValueOccurrence:
    """Return the existing ValueOccurrence for `value`, creating one if needed."""
    for existing in values:
        if existing.value == value:
            return existing

    created = ValueOccurrence(value=value)
    values.append(created)
    return created


def extract_query_params(
    entries: List[Dict[str, Any]],
    value_length_threshold: int = 0,
) -> List[TrackedValue]:
    """Collect every query string param name -> its distinct values.

    Values shorter than value_length_threshold are considered
    meaningless (e.g. flags, single chars) and skipped.
    """
    params: Dict[str, TrackedValue] = {}

    for entry in entries:
        request = entry.get("request", {})
        url = request.get("url", "")
        method = request.get("method", "")
        connection_id = entry.get("_connectionId", "")
        query_string = request.get("queryString", [])  # list of {name, value}

        for qp in query_string:
            name = qp.get("name", "")
            value = qp.get("value", "")

            if len(value) < value_length_threshold:
                continue

            tracked = params.setdefault(name, TrackedValue(key=name))
            tracked.appearances += 1

            value_occurrence = _find_or_create_value(tracked.values, value)
            value_occurrence.appearances += 1
            value_occurrence.requests.append(
                RequestRef(connection_id=connection_id, method=method, url=url)
            )

    return list(params.values())


def extract_cookies(
    entries: List[Dict[str, Any]],
    value_length_threshold: int = 0,
) -> List[TrackedValue]:
    """Collect every cookie name -> its distinct values (with security flags).

    Values shorter than value_length_threshold are considered
    meaningless (e.g. flags, single chars) and skipped.
    """
    cookies: Dict[str, TrackedValue] = {}

    for entry in entries:
        request = entry.get("request", {})
        url = request.get("url", "")
        method = request.get("method", "")
        connection_id = entry.get("_connectionId", "")
        request_cookies = request.get("cookies", [])  # list of cookie objects

        for ck in request_cookies:
            name = ck.get("name", "")
            value = ck.get("value", "")

            if len(value) < value_length_threshold:
                continue

            tracked = cookies.setdefault(name, TrackedValue(key=name))
            tracked.appearances += 1

            value_occurrence = _find_or_create_value(tracked.values, value)
            value_occurrence.appearances += 1
            value_occurrence.requests.append(
                CookieRequestRef(
                    connection_id=connection_id,
                    method=method,
                    url=url,
                    domain=ck.get("domain"),
                    path=ck.get("path"),
                    http_only=ck.get("httpOnly"),
                    secure=ck.get("secure"),
                    same_site=ck.get("sameSite"),
                    expires=ck.get("expires"),
                )
            )

    return list(cookies.values())


def extract_post_data(entries: List[Dict[str, Any]]) -> List[PostDataEntry]:
    """Collect raw POST bodies for every request that has one."""
    post_data_list: List[PostDataEntry] = []

    for entry in entries:
        request = entry.get("request", {})
        post_data = request.get("postData")

        if not post_data:
            continue  # no body on this request, skip

        post_data_list.append(
            PostDataEntry(
                connection_id=entry.get("_connectionId", ""),
                url=request.get("url", ""),
                method=request.get("method", ""),
                mime_type=post_data.get("mimeType"),
                post_data=post_data.get("text", ""),
            )
        )

    return post_data_list


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


def build_output(
    entries: List[Dict[str, Any]],
    value_length_threshold: int = 0,
) -> Dict[str, Any]:
    """Run all extractors and assemble the final output structure."""
    params = extract_query_params(entries, value_length_threshold)
    cookies = extract_cookies(entries, value_length_threshold)
    post_data = extract_post_data(entries)

    return {
        "params": [asdict(tv) for tv in params],
        "cookies": [asdict(tv) for tv in cookies],
        "postdata": [asdict(pd) for pd in post_data],
    }


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def extract(input_path: str, value_length_threshold: int = 0) -> Dict[str, Any]:

    har = load_har(input_path)
    entries = har.get("log", {}).get("entries", [])

    result = build_output(entries, value_length_threshold)

    return result


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python har_extract.py <input.har> <output.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    result = extract(input_path, 10)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Done. Wrote output to {output_path}")


if __name__ == "__main__":
    main()
