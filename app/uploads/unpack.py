"""Entpackt Uploads (ZIP oder Ordner) und listet alle Bilddateien."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path

_SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


class UnpackError(Exception):
    """Wird geworfen, wenn ein Upload nicht entpackt werden kann."""


@dataclass
class UnpackedUpload:
    """Ergebnis eines Entpackvorgangs."""

    root: Path
    photos: list[Path] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)  # (Pfad, Grund)

    @property
    def count(self) -> int:
        return len(self.photos)


def is_supported_photo(path: Path) -> bool:
    return path.suffix.lower() in _SUPPORTED_EXT


def unpack_upload(source: Path, workdir: Path) -> UnpackedUpload:
    """Entpackt ZIP oder listet einen Ordner. Gibt alle Bilddateien zurück.

    - ``source`` ist entweder ein ZIP-File oder ein Verzeichnis.
    - ``workdir`` ist das Zielverzeichnis für ZIP-Extraktion.
    - Skipped-Einträge enthalten Nicht-Bild-Dateien, symlinks (aus Sicherheit),
      Zip-Slip-Verdachtsfälle.
    """
    if not source.exists():
        raise UnpackError(f"Quelle existiert nicht: {source}")

    workdir.mkdir(parents=True, exist_ok=True)
    photos: list[Path] = []
    skipped: list[tuple[Path, str]] = []
    root_path = workdir

    if source.is_file() and source.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(source, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    # Zip-Slip-Schutz: keine absoluten Pfade, keine ".."
                    member_name = info.filename
                    if member_name.startswith(("/", "\\")) or ".." in Path(member_name).parts:
                        skipped.append((Path(member_name), "unsicherer Pfad"))
                        continue
                    target = workdir / member_name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, target.open("wb") as dst:
                        dst.write(src.read())
        except zipfile.BadZipFile as exc:
            raise UnpackError(f"ZIP nicht lesbar: {exc}") from exc

        # Iteriere jetzt über extrahierte Dateien
        for path in sorted(workdir.rglob("*")):
            if not path.is_file():
                continue
            if path.is_symlink():
                skipped.append((path, "Symlink"))
                continue
            if is_supported_photo(path):
                photos.append(path)
            else:
                skipped.append((path, f"Unbekannte Endung {path.suffix}"))

    elif source.is_dir():
        root_path = source
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            if path.is_symlink():
                skipped.append((path, "Symlink"))
                continue
            if is_supported_photo(path):
                photos.append(path)
            else:
                skipped.append((path, f"Unbekannte Endung {path.suffix}"))

    elif source.is_file() and is_supported_photo(source):
        # Einzelnes Foto
        root_path = source.parent
        photos.append(source)

    else:
        raise UnpackError(
            f"Nicht unterstützt: {source} — erwartet ZIP, Ordner oder Bild"
        )

    return UnpackedUpload(root=root_path, photos=photos, skipped=skipped)
