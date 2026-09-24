"""HTTP-Tests für den /analyze-Endpoint mit Mock-Provider."""

from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.main import create_app


@pytest.fixture()
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    db_path = tmp_path / "api.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    import app.core.db as db_module

    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_SessionLocal", TestSession)

    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "storage_path", tmp_path / "storage")
    (tmp_path / "storage" / "uploads").mkdir(parents=True, exist_ok=True)

    app = create_app()
    with TestClient(app) as client:
        yield client
    engine.dispose()


def _jpg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color="gray").save(buf, "JPEG")
    return buf.getvalue()


def test_analyze_via_mock_provider(api_client: TestClient) -> None:
    # Projekt anlegen + Foto hochladen
    pid = api_client.post("/api/projects", json={"name": "P", "contractor": "F"}).json()["id"]
    files = [("files", ("NVT_7107.jpg", _jpg_bytes(), "image/jpeg"))]
    api_client.post(f"/api/projects/{pid}/uploads", files=files, data={"run_ocr": "false"})

    nvts = api_client.get(f"/api/projects/{pid}/nvts").json()
    nid = nvts[0]["id"]

    r = api_client.post(
        f"/api/projects/{pid}/nvts/{nid}/analyze",
        params={"provider_override": "mock"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["environment_created"] is True
    # Mock ohne hinterlegten Response → alles unknown → manuelle Prüfung
    assert body["manual_review_required"] is True
    assert body["status"] == "NEEDS_REVIEW"


def test_analyze_unknown_nvt_404(api_client: TestClient) -> None:
    pid = api_client.post("/api/projects", json={"name": "P", "contractor": "F"}).json()["id"]
    r = api_client.post(
        f"/api/projects/{pid}/nvts/00000000-0000-0000-0000-000000000000/analyze",
        params={"provider_override": "mock"},
    )
    assert r.status_code == 404


def test_analyze_anthropic_without_key_400(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "anthropic_api_key", None)

    pid = api_client.post("/api/projects", json={"name": "P", "contractor": "F"}).json()["id"]
    api_client.post(
        f"/api/projects/{pid}/uploads",
        files=[("files", ("NVT_7107.jpg", _jpg_bytes(), "image/jpeg"))],
        data={"run_ocr": "false"},
    )
    nvts = api_client.get(f"/api/projects/{pid}/nvts").json()
    nid = nvts[0]["id"]

    r = api_client.post(
        f"/api/projects/{pid}/nvts/{nid}/analyze",
        params={"provider_override": "anthropic"},
    )
    assert r.status_code == 400
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]
