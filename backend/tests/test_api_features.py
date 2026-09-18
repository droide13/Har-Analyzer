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


def test_overview_endpoint(client: TestClient, upload_id: str) -> None:
    response = client.get(f"/api/har/{upload_id}/overview")
    body = response.json()
    assert response.status_code == 200
    assert body["summary"]["total_requests"] == 5
    assert body["method_counts"] == {"GET": 4, "POST": 1}
    assert "example.com" in body["domain_map"]
    assert body["first_party_domain"] == "example.com"


def test_overview_unknown_upload_returns_404(client: TestClient) -> None:
    assert client.get("/api/har/does-not-exist/overview").status_code == 404


def test_cookies_endpoint(client: TestClient, upload_id: str) -> None:
    response = client.get(f"/api/har/{upload_id}/cookies")
    body = response.json()
    assert response.status_code == 200
    assert body["metrics"]["total"] == 4
    names = {row["Name"] for row in body["aggregated"]}
    assert names == {"session", "tracking_id"}


def test_query_params_endpoint(client: TestClient, upload_id: str) -> None:
    response = client.get(f"/api/har/{upload_id}/query-params")
    body = response.json()
    assert response.status_code == 200
    assert body["metrics"]["total"] == 2
    assert body["metrics"]["unique_names"] == 1


def test_identifiers_endpoint_applies_thresholds(client: TestClient, upload_id: str) -> None:
    # Defaults (min_appearances=20) filter out everything in this tiny fixture.
    default_response = client.get(f"/api/har/{upload_id}/identifiers").json()
    assert default_response["cookies"] == []
    assert default_response["query_params"] == []

    # Loosened thresholds surface "session" (3 appearances, 2 unique values).
    loosened = client.get(
        f"/api/har/{upload_id}/identifiers",
        params={
            "min_appearances": 3,
            "max_unique_values": 2,
            "min_avg_length": 0,
            "min_avg_entropy": 0,
        },
    ).json()
    cookie_keys = {row["key"] for row in loosened["cookies"]}
    assert "session" in cookie_keys
    session_row = next(row for row in loosened["cookies"] if row["key"] == "session")
    assert len(session_row["values"]) == 2


def test_identifiers_endpoint_unknown_upload_returns_404(client: TestClient) -> None:
    assert client.get("/api/har/does-not-exist/identifiers").status_code == 404
