"""Klassifikation: NVT-Erkennung, Umgebungs-Aggregation (später)."""

from app.classification.nvt_detector import (
    NvtDetection,
    NvtDetectionSource,
    detect_nvt_number,
    group_photos_by_nvt,
)

__all__ = [
    "NvtDetection",
    "NvtDetectionSource",
    "detect_nvt_number",
    "group_photos_by_nvt",
]
