"""HTTP-Tests: Projekt anlegen, Fotos hochladen, NVTs auslesen."""

from __future__ import annotations

import io
import zipfile
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
    """Frische SQLite-DB pro Test, gemountet in app.core.db."""
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

    # Storage-Pfad umlenken
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "storage_path", tmp_path / "storage")
    (tmp_path / "storage" / "uploads").mkdir(parents=True, exist_ok=True)

    app = create_app()
    with TestClient(app) as client:
        yield client
    engine.dispose()


def _jpg_bytes(color: str = "red", size: tuple[int, int] = (16, 16)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, "JPEG")
    return buf.getvalue()


def test_health(api_client: TestClient) -> None:
    r = api_client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_project_lifecycle(api_client: TestClient) -> None:
    r = api_client.post("/api/projects", json={"name": "Roxel", "contractor": "Firma"})
    assert r.status_code == 201
    pid = r.json()["id"]

    r = api_client.get("/api/projects")
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())

    r = api_client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204

    r = api_client.get(f"/api/projects/{pid}")
    assert r.status_code == 404


def test_upload_flat_files(api_client: TestClient) -> None:
    r = api_client.post("/api/projects", json={"name": "Roxel", "contractor": "Firma"})
    pid = r.json()["id"]

    files = [
        ("files", ("NVT_7107.jpg", _jpg_bytes("red"), "image/jpeg")),
        ("files", ("NVT_7108.jpg", _jpg_bytes("blue"), "image/jpeg")),
    ]
    r = api_client.post(f"/api/projects/{pid}/uploads", files=files, data={"run_ocr": "false"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_photos"] == 2
    assert body["new_nvts"] == 2

    r = api_client.get(f"/api/projects/{pid}/nvts")
    assert r.status_code == 200
    nvts = r.json()
    assert {n["nvt_number"] for n in nvts} == {"7107", "7108"}
    assert all(n["photo_count"] == 1 for n in nvts)


def test_upload_zip(api_client: TestClient) -> None:
    r = api_client.post("/api/projects", json={"name": "P", "contractor": "F"})
    pid = r.json()["id"]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("NVT_7107/front.jpg", _jpg_bytes("red"))
        zf.writestr("NVT_7107/side.jpg", _jpg_bytes("green"))
        zf.writestr("NVT_7108/01.jpg", _jpg_bytes("blue"))
    buf.seek(0)

    files = [("files", ("upload.zip", buf.getvalue(), "application/zip"))]
    r = api_client.post(f"/api/projects/{pid}/uploads", files=files, data={"run_ocr": "false"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_photos"] == 3
    assert body["new_nvts"] == 2
    assert body["updated_nvts"] == 1


def test_upload_to_unknown_project_404(api_client: TestClient) -> None:
    files = [("files", ("NVT_7107.jpg", _jpg_bytes(), "image/jpeg"))]
    r = api_client.post(
        "/api/projects/00000000-0000-0000-0000-000000000000/uploads",
        files=files,
        data={"run_ocr": "false"},
    )
    assert r.status_code == 404
