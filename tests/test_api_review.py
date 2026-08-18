"""Tests für POST .../nvts/{id}/review."""

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
    engine = create_engine(
        f"sqlite:///{tmp_path / 'api.db'}", future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    import app.core.db as db_module

    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_SessionLocal", SessionLocal)

    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "storage_path", tmp_path / "storage")
    (tmp_path / "storage" / "uploads").mkdir(parents=True, exist_ok=True)

    with TestClient(create_app()) as client:
        yield client
    engine.dispose()


def _jpg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color="gray").save(buf, "JPEG")
    return buf.getvalue()


def _nvt_id_without_decision(client: TestClient) -> tuple[str, str]:
    pid = client.post("/api/projects", json={"name": "P", "contractor": "F"}).json()["id"]
    client.post(
        f"/api/projects/{pid}/uploads",
        files=[("files", ("NVT_7107.jpg", _jpg_bytes(), "image/jpeg"))],
        data={"run_ocr": "false"},
    )
    nid = client.get(f"/api/projects/{pid}/nvts").json()[0]["id"]
    return pid, nid


def test_approve_without_decision_rejected(api_client: TestClient) -> None:
    pid, nid = _nvt_id_without_decision(api_client)
    r = api_client.post(
        f"/api/projects/{pid}/nvts/{nid}/review",
        json={"action": "APPROVED", "reviewer": "tester"},
    )
    assert r.status_code == 400


def test_full_flow_approve(api_client: TestClient) -> None:
    pid, nid = _nvt_id_without_decision(api_client)
    api_client.post(f"/api/projects/{pid}/nvts/{nid}/analyze", params={"provider_override": "mock"})
    api_client.post(f"/api/projects/{pid}/nvts/{nid}/decide")

    r = api_client.post(
        f"/api/projects/{pid}/nvts/{nid}/review",
        json={"action": "APPROVED", "reviewer": "tester", "comment": "passt"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "APPROVED"
    assert body["action"] == "APPROVED"

    # Statushistorie via NVT-Endpoint prüfbar
    nvt = api_client.get(f"/api/projects/{pid}/nvts/{nid}").json()
    assert nvt["status"] == "APPROVED"


def test_reject_flow(api_client: TestClient) -> None:
    pid, nid = _nvt_id_without_decision(api_client)
    api_client.post(f"/api/projects/{pid}/nvts/{nid}/analyze", params={"provider_override": "mock"})
    api_client.post(f"/api/projects/{pid}/nvts/{nid}/decide")

    r = api_client.post(
        f"/api/projects/{pid}/nvts/{nid}/review",
        json={"action": "REJECTED", "reviewer": "tester"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED"


def test_review_unknown_nvt_404(api_client: TestClient) -> None:
    pid = api_client.post("/api/projects", json={"name": "P", "contractor": "F"}).json()["id"]
    r = api_client.post(
        f"/api/projects/{pid}/nvts/00000000-0000-0000-0000-000000000000/review",
        json={"action": "APPROVED", "reviewer": "tester"},
    )
    assert r.status_code == 404
