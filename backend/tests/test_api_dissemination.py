import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def upload_id(client: TestClient, sample_har_bytes: bytes) -> str:
    response = client.post(
        "/api/har/upload",
        files={"file": ("sample.har", sample_har_bytes, "application/json")},
    )
    return response.json()["upload_id"]


def test_dissemination_keys_sorted_by_sightings(client: TestClient, upload_id: str) -> None:
    keys = client.get(f"/api/har/{upload_id}/dissemination/keys").json()
    assert keys[0] == "session"


def test_dissemination_timeline(client: TestClient, upload_id: str) -> None:
    response = client.get(f"/api/har/{upload_id}/dissemination/timeline", params={"key": "session"})
    body = response.json()
    assert response.status_code == 200
    assert body["sightings"] == 3
    assert body["distinct_values"] == 2
    assert body["first_seen"]["origin"] == "Request Cookie"
    assert len(body["timeline"]) == 3
    # The fixture's entries carry no _initiator data, so there's nothing to
    # trace back through -- an empty chain, not an error.
    assert body["initiator_chain"] == []


def test_dissemination_timeline_unknown_key_returns_404(client: TestClient, upload_id: str) -> None:
    response = client.get(
        f"/api/har/{upload_id}/dissemination/timeline", params={"key": "does-not-exist"}
    )
    assert response.status_code == 404


def test_dissemination_search_finds_matches_and_aggregates_by_domain(
    client: TestClient, upload_id: str
) -> None:
    response = client.post(
        f"/api/har/{upload_id}/dissemination/search",
        json={"key": "token", "encodings": []},
    )
    body = response.json()
    assert response.status_code == 200
    assert [row["index"] for row in body["matches"]] == [0, 3]
    assert body["by_domain"][0]["Domain"] == "example.com"
    assert body["by_domain"][0]["Entries Hit"] == 2


def test_dissemination_search_narrow_discards_and_highlight_flags(
    client: TestClient, upload_id: str
) -> None:
    # Narrow to only status:404 (entry 3), independent of the by-domain totals.
    narrowed = client.post(
        f"/api/har/{upload_id}/dissemination/search",
        json={"key": "token", "encodings": [], "narrow": "status:404"},
    ).json()
    assert [row["index"] for row in narrowed["matches"]] == [3]
    assert narrowed["by_domain"][0]["Entries Hit"] == 2  # unaffected by narrow

    highlighted = client.post(
        f"/api/har/{upload_id}/dissemination/search",
        json={"key": "token", "encodings": [], "highlight": "status:404"},
    ).json()
    flags = {row["index"]: row["highlighted"] for row in highlighted["matches"]}
    assert flags == {0: False, 3: True}


def test_dissemination_search_unknown_key_returns_404(client: TestClient, upload_id: str) -> None:
    response = client.post(
        f"/api/har/{upload_id}/dissemination/search",
        json={"key": "does-not-exist", "encodings": []},
    )
    assert response.status_code == 404


def test_dissemination_search_ground_truth_is_opt_in_and_badges_per_key(
    client: TestClient, sample_har_dict: dict
) -> None:
    sample_har_dict["log"]["_analysis"] = {
        "domain": "example.com",
        "platform": "web",
        "interact": "login",
        "cookies": "accept",
        "visit": "first",
        "extra": "000",
        "captured_at": "2026-01-01T10:00:00+00:00",
        "standardized_filename": "x.har",
        "ground_truth": [{"key": "Session Token", "value": "abc123"}],
    }
    upload = client.post(
        "/api/har/upload",
        files={"file": ("tagged.har", json.dumps(sample_har_dict).encode("utf-8"), "application/json")},
    )
    upload_id = upload.json()["upload_id"]

    # Omitting gt_keys entirely runs no ground-truth check at all.
    unrequested = client.post(
        f"/api/har/{upload_id}/dissemination/search", json={"key": "token", "encodings": []}
    ).json()
    assert all(not row["highlighted"] for row in unrequested["matches"])

    body = client.post(
        f"/api/har/{upload_id}/dissemination/search",
        json={"key": "token", "encodings": [], "gt_keys": ["Session Token"]},
    ).json()
    # Both entries traced for "token" (0 and 3) also carry the ground-truth value.
    flags = {row["index"]: row["highlighted"] for row in body["matches"]}
    assert flags == {0: True, 3: True}
    badge_labels = [b["label"] for b in body["matches"][0]["badges"]]
    assert "Session Token match: Query Params (plain)" in badge_labels
