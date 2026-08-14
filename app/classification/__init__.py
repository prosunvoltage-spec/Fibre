"""Klassifizierung eingehender Fotos → NVT-Zuweisung + Umgebungsprofil.

Aktuell in Phase 4: nur ``nvt_detector`` (Zuordnung Foto→NVT). Der
``environment_builder`` (Vision-Aggregation) kommt in Phase 5.
"""

from app.classification.nvt_detector import (
    NvtAssignment,
    NvtIdSource,
    detect_nvt,
)

__all__ = ["NvtAssignment", "NvtIdSource", "detect_nvt"]
