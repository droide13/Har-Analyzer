"""Shared pytest fixtures: a small synthetic HAR file exercising the cases
the ported logic cares about (repeated query/cookie values, mixed statuses,
a second domain, a POST body). Kept tiny and hand-written rather than using
one of the real multi-hundred-MB sample captures in src/captures/, which
are local-only and gitignored -- see readme.md for how to load those in a
running instance for manual/E2E checks.
"""

import base64
import json

import pytest

# A value that appears ONLY in its Base64-encoded form in the fixture below,
# so encoding-aware matching can be tested in isolation from plain matching.
ENCODED_ONLY_VALUE = "secret-value-xyz"
ENCODED_ONLY_VALUE_B64 = base64.b64encode(ENCODED_ONLY_VALUE.encode("utf-8")).decode("ascii")

SAMPLE_HAR: dict = {
    "log": {
        "version": "1.2",
        "creator": {"name": "pytest", "version": "0.0.0"},
        "entries": [
            {
                "startedDateTime": "2026-01-01T10:00:00.000Z",
                "time": 120.5,
                "request": {
                    "method": "GET",
                    "url": "https://example.com/api/data?token=abc123",
                    "headers": [{"name": "User-Agent", "value": "pytest"}],
                    "cookies": [{"name": "session", "value": "sess-1"}],
                    "queryString": [{"name": "token", "value": "abc123"}],
                },
                "response": {
                    "status": 200,
                    "statusText": "OK",
                    "headers": [{"name": "Content-Type", "value": "application/json"}],
                    "cookies": [{"name": "tracking_id", "value": "trk-999"}],
                    "content": {"mimeType": "application/json", "text": '{"ok": true}'},
                    "bodySize": 42,
                    "headersSize": 120,
                },
            },
            {
                "startedDateTime": "2026-01-01T10:00:01.000Z",
                "time": 80.0,
                "request": {
                    "method": "POST",
                    "url": "https://example.com/login",
                    "headers": [],
                    "cookies": [],
                    "queryString": [],
                    "postData": {"mimeType": "application/x-www-form-urlencoded",
                                 "text": "user=alice&pass=secret"},
                },
                "response": {
                    "status": 302,
                    "statusText": "Found",
                    "headers": [],
                    "cookies": [{"name": "session", "value": "sess-2"}],
                    "content": {"mimeType": "text/html", "text": ""},
                    "bodySize": 0,
                    "headersSize": 90,
                },
            },
            {
                "startedDateTime": "2026-01-01T10:00:02.000Z",
                "time": 15.2,
                "request": {
                    "method": "GET",
                    "url": "https://cdn.example.com/assets/app.js",
                    "headers": [],
                    "cookies": [],
                    "queryString": [],
                },
                "response": {
                    "status": 200,
                    "statusText": "OK",
                    "headers": [],
                    "cookies": [],
                    "content": {"mimeType": "application/javascript", "text": "console.log(1)"},
                    "bodySize": 512,
                    "headersSize": 80,
                },
            },
            {
                "startedDateTime": "2026-01-01T10:00:03.000Z",
                "time": 30.0,
                "request": {
                    "method": "GET",
                    "url": "https://example.com/api/data?token=abc123",
                    "headers": [{"name": "User-Agent", "value": "pytest"}],
                    "cookies": [{"name": "session", "value": "sess-1"}],
                    "queryString": [{"name": "token", "value": "abc123"}],
                },
                "response": {
                    "status": 404,
                    "statusText": "Not Found",
                    "headers": [],
                    "cookies": [],
                    "content": {"mimeType": "application/json", "text": '{"error": "gone"}'},
                    "bodySize": 20,
                    "headersSize": 60,
                },
            },
            {
                "startedDateTime": "2026-01-01T10:00:04.000Z",
                "time": 10.0,
                "request": {
                    "method": "GET",
                    "url": "https://example.com/signed",
                    "headers": [],
                    "cookies": [],
                    "queryString": [],
                },
                "response": {
                    "status": 200,
                    "statusText": "OK",
                    "headers": [{"name": "X-Signature", "value": ENCODED_ONLY_VALUE_B64}],
                    "cookies": [],
                    "content": {"mimeType": "text/plain", "text": ""},
                    "bodySize": 0,
                    "headersSize": 40,
                },
            },
        ],
    }
}


@pytest.fixture
def sample_har_dict() -> dict:
    """The synthetic HAR structure as a plain dict (mutate a copy freely)."""
    return json.loads(json.dumps(SAMPLE_HAR))


@pytest.fixture
def sample_har_bytes(sample_har_dict: dict) -> bytes:
    """The synthetic HAR structure serialized to bytes, as an upload would arrive."""
    return json.dumps(sample_har_dict).encode("utf-8")
