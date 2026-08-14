"""Upload- und Foto-Ingest.

Nimmt ZIPs oder Ordner-Trees entgegen, schreibt Fotos in das
projektbezogene Storage (siehe ``docs/ARCHITECTURE.md §3``), berechnet
SHA-256 für Deduplizierung und extrahiert EXIF-Metadaten.
"""

from app.uploads.ingest import (
    IngestedPhoto,
    IngestError,
    ingest_bytes_as_zip,
    ingest_directory,
    ingest_files,
)

__all__ = [
    "IngestError",
    "IngestedPhoto",
    "ingest_bytes_as_zip",
    "ingest_directory",
    "ingest_files",
]
