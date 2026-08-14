"""End-to-End Integration-Test des Upload-Endpoints.

Deckt das Abnahmekriterium PROJECT_PLAN.md Phase 4 ab:
Ein Test-ZIP mit 5 NVT-Fotos ergibt 5 ``Nvt``-Records mit
korrekter ID und Adresse.

OCR wird durch ``MockOCRProvider`` ersetzt, damit der Test nicht von
Tesseract-Erkennungsqualität abhängt. Der Tesseract-Live-Test läuft
separat in ``test_ocr_tesseract.py``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db, get_ocr_provider
from app.config import get_settings
from app.core.db import Base
from app.core.models import Nvt, Photo
from app.main import app
from app.ocr.base import OcrResult
from app.ocr.mock_provider import MockOCRProvider
from tests.fixtures.photo_generator import (
    build_zip_from_specs,
    canonical_five_nvt_specs,
    render_photo,
)


@pytest.fixture()
def api_engine(tmp_path: Path) -> Iterator[Engine]:
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def api_client(
    api_engine: Engine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    # Storage-Root in tmp legen
    monkeypatch.setattr(get_settings(), "storage_path", tmp_path / "storage", raising=False)

    SessionLocal = sessionmaker(bind=api_engine, autoflush=False, autocommit=False, future=True)

    def _db_override() -> Iterator[Session]:
        s = SessionLocal()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    # OCR-Antworten aus den kanonischen Fixtures ableiten
    ocr_map: dict[str, OcrResult] = {}
    for spec in canonical_five_nvt_specs():
        blob = render_photo(spec)
        sha = hashlib.sha256(blob).hexdigest()
        text = " ".join(spec.overlay_lines).replace("Muenster", "Münster").replace(
            "Muensterstrasse", "Münsterstrasse"
        )
        ocr_map[sha] = OcrResult(
            text=text,
            blocks=[],
            language="deu",
            provider="mock",
            provider_version="1",
            image_width=spec.size[0],
            image_height=spec.size[1],
        )

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_ocr_provider] = lambda: MockOCRProvider(ocr_map)

    with TestClient(app) as client:
        yield client, SessionLocal

    app.dependency_overrides.clear()


def _create_project(client: TestClient) -> str:
    payload = {
        "name": "Roxel Phase-4 Test",
        "contractor": "Helder Santos GmbH",
        "ruleset_version": "v1",
        "vision_provider": "mock",
    }
    resp = client.post("/api/projects", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_upload_zip_creates_five_nvts(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = api_client
    project_id = _create_project(client)

    zip_bytes = build_zip_from_specs(canonical_five_nvt_specs())
    resp = client.post(
        f"/api/projects/{project_id}/uploads",
        files={"files": ("roxel.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["ingested_files"] == 1
    assert len(body["per_nvt"]) == 5

    numbers = sorted(entry["nvt_number"] for entry in body["per_nvt"])
    assert numbers == ["7101", "7102", "7103", "7104", "7105"]
    assert all(entry["created"] is True for entry in body["per_nvt"])
    assert all(entry["photos_created"] == 1 for entry in body["per_nvt"])
    assert body["unassigned_photo_sha256"] == []

    # DB-Verifikation
    with SessionLocal() as session:
        nvts = session.query(Nvt).order_by(Nvt.nvt_number).all()
        assert [n.nvt_number for n in nvts] == ["7101", "7102", "7103", "7104", "7105"]
        for n in nvts:
            assert n.address_json is not None
            assert n.address_json["postal_code"] in {"48161", "48159", "48143"}
            assert n.address_json["city"] == "Münster"
        photos = session.query(Photo).all()
        assert len(photos) == 5


def test_upload_zip_second_time_dedupes(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = api_client
    project_id = _create_project(client)
    zip_bytes = build_zip_from_specs(canonical_five_nvt_specs())

    r1 = client.post(
        f"/api/projects/{project_id}/uploads",
        files={"files": ("roxel.zip", zip_bytes, "application/zip")},
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/api/projects/{project_id}/uploads",
        files={"files": ("roxel.zip", zip_bytes, "application/zip")},
    )
    assert r2.status_code == 201
    body = r2.json()
    # Alle 5 NVTs existierten bereits, alle 5 Fotos sind Duplikate
    assert all(entry["created"] is False for entry in body["per_nvt"])
    assert all(entry["photos_created"] == 0 for entry in body["per_nvt"])
    assert all(entry["photos_skipped_duplicate"] == 1 for entry in body["per_nvt"])

    with SessionLocal() as session:
        assert session.query(Nvt).count() == 5
        assert session.query(Photo).count() == 5


def test_upload_single_jpg(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, SessionLocal = api_client
    project_id = _create_project(client)

    specs = canonical_five_nvt_specs()[:1]  # nur NVT_7101
    photo_bytes = render_photo(specs[0])

    resp = client.post(
        f"/api/projects/{project_id}/uploads",
        files={"files": (specs[0].filename, photo_bytes, "image/jpeg")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["per_nvt"]) == 1
    assert body["per_nvt"][0]["nvt_number"] == "7101"


def test_upload_with_nvt_override(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = api_client
    project_id = _create_project(client)
    specs = canonical_five_nvt_specs()[:1]
    photo_bytes = render_photo(specs[0])

    resp = client.post(
        f"/api/projects/{project_id}/uploads",
        files={"files": (specs[0].filename, photo_bytes, "image/jpeg")},
        data={"nvt_overrides": '{"NVT_7101.jpg": "7999"}'},
    )
    assert resp.status_code == 201, resp.text
    entry = resp.json()["per_nvt"][0]
    assert entry["nvt_number"] == "7999"
    assert any("Datei=7101" in w or "Datei" in w for w in entry["warnings"])


def test_upload_project_not_found(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api_client
    # ohne _create_project → 404
    fake_id = "00000000-0000-0000-0000-000000000001"
    resp = client.post(
        f"/api/projects/{fake_id}/uploads",
        files={"files": ("x.jpg", b"junk", "image/jpeg")},
    )
    assert resp.status_code == 404


def test_upload_bad_json_overrides(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api_client
    project_id = _create_project(client)
    specs = canonical_five_nvt_specs()[:1]
    photo_bytes = render_photo(specs[0])
    resp = client.post(
        f"/api/projects/{project_id}/uploads",
        files={"files": (specs[0].filename, photo_bytes, "image/jpeg")},
        data={"nvt_overrides": "not-json"},
    )
    assert resp.status_code == 400
