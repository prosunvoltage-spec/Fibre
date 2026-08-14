"""Tests für ``app/uploads/ingest.py``."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from app.uploads import (
    IngestError,
    ingest_bytes_as_zip,
    ingest_directory,
    ingest_files,
)
from tests.fixtures.photo_generator import (
    PhotoSpec,
    build_zip_from_specs,
    canonical_five_nvt_specs,
    render_photo,
    write_directory_from_specs,
)


@pytest.fixture()
def storage(tmp_path: Path) -> Path:
    return tmp_path / "storage"


def test_ingest_directory_nested_layout(storage: Path, tmp_path: Path) -> None:
    src = tmp_path / "src"
    write_directory_from_specs(
        src,
        [
            PhotoSpec(filename="NVT_7101/01.jpg", overlay_lines=["NVT 7101 A"]),
            PhotoSpec(filename="NVT_7101/02.jpg", overlay_lines=["NVT 7101 B"]),
            PhotoSpec(filename="NVT_7102/seite.jpg", overlay_lines=["NVT 7102"]),
        ],
    )

    project_id = uuid4()
    result = ingest_directory(src, project_id=project_id, storage_root=storage)
    assert len(result) == 3
    hints = {p.original_filename: p.folder_nvt_hint for p in result}
    assert hints == {"01.jpg": "7101", "02.jpg": "7101", "seite.jpg": "7102"}
    for p in result:
        assert p.filename_nvt_hint is None
        assert p.stored_path.exists()


def test_ingest_zip_flat_layout(storage: Path) -> None:
    specs = [
        PhotoSpec(filename="NVT_7103.jpg", overlay_lines=["NVT 7103"]),
        PhotoSpec(filename="NVT_7104_seitlich.jpg", overlay_lines=["NVT 7104"]),
    ]
    result = ingest_bytes_as_zip(
        build_zip_from_specs(specs),
        project_id=uuid4(),
        storage_root=storage,
    )
    assert [p.original_filename for p in result] == [
        "NVT_7103.jpg",
        "NVT_7104_seitlich.jpg",
    ]
    assert [p.filename_nvt_hint for p in result] == ["7103", "7104"]


def test_ingest_zip_ignores_macos_junk(storage: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("NVT_7101.jpg", render_photo(PhotoSpec("x.jpg", ["hi"])))
        zf.writestr("__MACOSX/._NVT_7101.jpg", b"junk")
        zf.writestr(".DS_Store", b"junk")

    result = ingest_bytes_as_zip(buf.getvalue(), project_id=uuid4(), storage_root=storage)
    assert len(result) == 1


def test_ingest_zip_rejects_zip_slip(storage: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.jpg", render_photo(PhotoSpec("x.jpg", ["a"])))

    with pytest.raises(IngestError):
        ingest_bytes_as_zip(buf.getvalue(), project_id=uuid4(), storage_root=storage)


def test_ingest_zip_rejects_absolute_path(storage: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zi = zipfile.ZipInfo("/tmp/evil.jpg")
        zf.writestr(zi, render_photo(PhotoSpec("x.jpg", ["a"])))

    with pytest.raises(IngestError):
        ingest_bytes_as_zip(buf.getvalue(), project_id=uuid4(), storage_root=storage)


def test_ingest_zip_bad_zip(storage: Path) -> None:
    with pytest.raises(IngestError):
        ingest_bytes_as_zip(b"not a zip", project_id=uuid4(), storage_root=storage)


def test_duplicate_within_batch(storage: Path) -> None:
    photo_bytes = render_photo(PhotoSpec("orig.jpg", ["gleicher Inhalt"]))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("NVT_7105/a.jpg", photo_bytes)
        zf.writestr("NVT_7105/b.jpg", photo_bytes)

    result = ingest_bytes_as_zip(buf.getvalue(), project_id=uuid4(), storage_root=storage)
    assert len(result) == 2
    assert result[0].is_duplicate is False
    assert result[1].is_duplicate is True
    assert result[0].sha256 == result[1].sha256


def test_duplicate_against_known_sha(storage: Path) -> None:
    known = {"a" * 64}  # dummy
    # Wir kennen den echten sha256 erst nach ingest — daher zwei Läufe
    project_id = uuid4()
    first = ingest_bytes_as_zip(
        build_zip_from_specs([PhotoSpec("NVT_7106.jpg", ["a"])]),
        project_id=project_id,
        storage_root=storage,
    )
    assert first[0].is_duplicate is False

    # Zweiter Lauf mit bekanntem sha256
    known.add(first[0].sha256)
    second_zip = io.BytesIO()
    with zipfile.ZipFile(second_zip, "w") as zf:
        zf.writestr("NVT_7106.jpg", first[0].stored_path.read_bytes())
    second = ingest_bytes_as_zip(
        second_zip.getvalue(),
        project_id=project_id,
        storage_root=storage,
        known_sha256=known,
    )
    assert second[0].is_duplicate is True


def test_ingest_files_direct(storage: Path) -> None:
    files = [
        ("NVT_7107.jpg", render_photo(PhotoSpec("x.jpg", ["NVT 7107"]))),
        ("NVT_7108.jpg", render_photo(PhotoSpec("y.jpg", ["NVT 7108"]))),
    ]
    result = ingest_files(files, project_id=uuid4(), storage_root=storage)
    assert [p.filename_nvt_hint for p in result] == ["7107", "7108"]


def test_ingest_directory_non_image_ignored(storage: Path, tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "readme.txt").write_text("not an image")
    (src / "NVT_7101.jpg").write_bytes(render_photo(PhotoSpec("x.jpg", ["NVT 7101"])))
    result = ingest_directory(src, project_id=uuid4(), storage_root=storage)
    assert len(result) == 1
    assert result[0].original_filename == "NVT_7101.jpg"


def test_ingest_directory_missing(tmp_path: Path) -> None:
    with pytest.raises(IngestError):
        ingest_directory(tmp_path / "nichtda", project_id=uuid4(), storage_root=tmp_path)


def test_canonical_five_have_unique_shas(storage: Path) -> None:
    zip_bytes = build_zip_from_specs(canonical_five_nvt_specs())
    result = ingest_bytes_as_zip(zip_bytes, project_id=uuid4(), storage_root=storage)
    assert len(result) == 5
    assert len({p.sha256 for p in result}) == 5
