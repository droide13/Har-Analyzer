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
    assert response.status_code == 200
    return response.json()["upload_id"]


def test_upload_returns_entry_count(client: TestClient, sample_har_bytes: bytes) -> None:
    response = client.post(
        "/api/har/upload",
        files={"file": ("sample.har", sample_har_bytes, "application/json")},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["entry_count"] == 5
    assert body["filename"] == "sample.har"


def test_upload_rejects_invalid_json(client: TestClient) -> None:
    response = client.post(
        "/api/har/upload",
        files={"file": ("bad.har", b"not json", "application/json")},
    )
    assert response.status_code == 400


def test_list_entries_no_filter_returns_everything(client: TestClient, upload_id: str) -> None:
    response = client.get(f"/api/har/{upload_id}/entries")
    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 5
    assert body["filtered"] == 5
    assert len(body["items"]) == 5


def test_list_entries_filter_query_narrows_results(client: TestClient, upload_id: str) -> None:
    response = client.get(f"/api/har/{upload_id}/entries", params={"q": "status:404"})
    body = response.json()
    assert body["filtered"] == 1
    assert body["items"][0]["status"] == "404"


def test_list_entries_highlight_query_flags_without_discarding(
    client: TestClient, upload_id: str
) -> None:
    response = client.get(f"/api/har/{upload_id}/entries", params={"h": "abc123"})
    body = response.json()
    # 3 of 5 entries mention abc123 (two GETs on /api/data plus none else);
    # nothing gets discarded by a highlight-only query.
    assert body["filtered"] == 5
    assert body["highlighted"] == 2
    highlighted_indices = [item["index"] for item in body["items"] if item["highlighted"]]
    assert highlighted_indices == [0, 3]
    # Both matches land on the one page returned at the default page size.
    assert body["highlighted_pages"] == [1]


def test_list_entries_no_highlight_query_returns_empty_highlighted_pages(
    client: TestClient, upload_id: str
) -> None:
    response = client.get(f"/api/har/{upload_id}/entries")
    assert response.json()["highlighted_pages"] == []


def test_list_entries_pagination(client: TestClient, upload_id: str) -> None:
    # page_size's floor (10) matches the original UI's number_input min_value,
    # so 5 sample entries always fit on one page -- assert that, plus that a
    # page requested past the end clamps back to the last real page.
    page1 = client.get(f"/api/har/{upload_id}/entries", params={"page_size": 10, "page": 1}).json()
    assert page1["total_pages"] == 1
    assert [item["index"] for item in page1["items"]] == [0, 1, 2, 3, 4]

    clamped = client.get(
        f"/api/har/{upload_id}/entries", params={"page_size": 10, "page": 5}
    ).json()
    assert clamped["page"] == 1
    assert [item["index"] for item in clamped["items"]] == [0, 1, 2, 3, 4]


def test_list_entries_ground_truth_flags_matches(
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
        "ground_truth": [
            {"key": "E-mail", "value": "alice"},
            {"key": "IP Address", "value": "10.0.0.1"},  # never appears in the fixture
        ],
    }
    upload = client.post(
        "/api/har/upload",
        files={"file": ("tagged.har", json.dumps(sample_har_dict).encode("utf-8"), "application/json")},
    )
    upload_id = upload.json()["upload_id"]

    # Ground truth search is opt-in (a full scan) -- omitting gt_keys entirely
    # runs no check at all, not "check every tagged key".
    unrequested = client.get(f"/api/har/{upload_id}/entries").json()
    assert all(not item["highlighted"] for item in unrequested["items"])

    body = client.get(f"/api/har/{upload_id}/entries", params={"gt_keys": "E-mail,IP Address"}).json()
    flagged = [item["index"] for item in body["items"] if item["highlighted"]]
    assert flagged == [1]  # only the login POST body ("user=alice&pass=secret") mentions it
    badge_labels = [b["label"] for b in body["items"][1]["badges"]]
    assert any(label == "E-mail match: POST Data (plain)" for label in badge_labels)

    # Excluding the matching key drops the match entirely, not just its highlight.
    excluded = client.get(f"/api/har/{upload_id}/entries", params={"gt_keys": "IP Address"}).json()
    assert all(not item["highlighted"] for item in excluded["items"])


def test_list_entries_unknown_upload_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/har/does-not-exist/entries")
    assert response.status_code == 404


def test_entry_detail_returns_full_fields(client: TestClient, upload_id: str) -> None:
    response = client.get(f"/api/har/{upload_id}/entries/1")
    body = response.json()
    assert response.status_code == 200
    assert body["method"] == "POST"
    assert body["req_body"] == "user=alice&pass=secret"


def test_entry_detail_unknown_index_returns_404(client: TestClient, upload_id: str) -> None:
    response = client.get(f"/api/har/{upload_id}/entries/999")
    assert response.status_code == 404


def test_meta_endpoints_expose_shared_option_tables(client: TestClient) -> None:
    methods = client.get("/api/har/meta/methods").json()
    encodings = client.get("/api/har/meta/encodings").json()
    scopes = client.get("/api/har/meta/scopes").json()

    assert "GET" in methods and "POST" in methods
    assert "Base64" in encodings
    assert scopes["All fields"] == "any"
    assert scopes["Cookies"] == "cookies"
