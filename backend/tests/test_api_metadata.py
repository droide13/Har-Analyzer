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


def test_get_metadata_detects_domain_and_no_existing_analysis(
    client: TestClient, upload_id: str
) -> None:
    response = client.get(f"/api/har/{upload_id}/metadata")
    body = response.json()
    assert response.status_code == 200
    assert body["detected"]["first_request_domain"] == "example.com"
    assert body["detected"]["captured_at"] is not None
    assert "Custom domain..." in body["detected"]["domain_options"]
    assert body["existing_analysis"] is None


def test_generate_then_download_round_trip(client: TestClient, upload_id: str) -> None:
    # Nothing generated yet -> download 404s.
    assert client.get(f"/api/har/{upload_id}/metadata/download").status_code == 404

    generate = client.post(
        f"/api/har/{upload_id}/metadata/generate",
        json={
            "domain": "example.com",
            "interact": "login",
            "cookies": "accept",
            "visit": "first",
            "extra": "",
            "captured_at": "2026-01-01T10:00:00+00:00",
            "description": "test run",
        },
    )
    body = generate.json()
    assert generate.status_code == 200
    assert body["filename"].startswith("example.com-interact-LOG-cookies-ACC-visit-FIR")
    assert body["analysis"]["description"] == "test run"

    download = client.get(f"/api/har/{upload_id}/metadata/download")
    assert download.status_code == 200
    assert download.headers["content-disposition"] == f'attachment; filename="{body["filename"]}"'

    downloaded_har = download.json()
    assert downloaded_har["log"]["_analysis"]["standardized_filename"] == body["filename"]

    # A second GET /metadata still reflects the pristine upload, not the
    # just-generated copy -- matches the original re-reading the original
    # file bytes on every render rather than the frozen download snapshot.
    still_no_existing = client.get(f"/api/har/{upload_id}/metadata").json()
    assert still_no_existing["existing_analysis"] is None


def test_generate_rejects_empty_domain(client: TestClient, upload_id: str) -> None:
    response = client.post(
        f"/api/har/{upload_id}/metadata/generate",
        json={
            "domain": "   ",
            "interact": "login",
            "cookies": "accept",
            "visit": "first",
            "captured_at": "2026-01-01T10:00:00+00:00",
        },
    )
    assert response.status_code == 400


def test_generate_rejects_invalid_interact_code(client: TestClient, upload_id: str) -> None:
    response = client.post(
        f"/api/har/{upload_id}/metadata/generate",
        json={
            "domain": "example.com",
            "interact": "not-a-code",
            "cookies": "accept",
            "visit": "first",
            "captured_at": "2026-01-01T10:00:00+00:00",
        },
    )
    assert response.status_code == 400


def test_metadata_unknown_upload_returns_404(client: TestClient) -> None:
    assert client.get("/api/har/does-not-exist/metadata").status_code == 404


def test_naming_options_exposes_label_tables(client: TestClient) -> None:
    response = client.get("/api/naming/options")
    body = response.json()
    assert response.status_code == 200
    assert body["interact"]["login"] == "Login"
    assert body["cookies"]["accept"] == "Accept"
    assert body["visit"]["first"] == "First visit (fresh state)"
