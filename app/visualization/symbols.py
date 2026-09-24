"""Registry für Symbol-Assets (PNGs unter data/symbols/)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.config import get_settings
from app.core.enums import OverlaySymbolType


@dataclass(frozen=True)
class Symbol:
    type: OverlaySymbolType
    path: Path


class SymbolRegistry:
    """Lädt und cached die PNG-Assets für die Overlay-Symbole."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._cache: dict[OverlaySymbolType, Image.Image] = {}

    def path_for(self, symbol: OverlaySymbolType) -> Path:
        return self.root / f"{symbol.value}.png"

    def available(self, symbol: OverlaySymbolType) -> bool:
        return self.path_for(symbol).is_file()

    def load(self, symbol: OverlaySymbolType) -> Image.Image:
        if symbol in self._cache:
            return self._cache[symbol]
        p = self.path_for(symbol)
        if not p.is_file():
            raise FileNotFoundError(f"Symbol-Datei fehlt: {p}")
        img = Image.open(p).convert("RGBA")
        self._cache[symbol] = img
        return img


_default_registry: SymbolRegistry | None = None


def get_symbol_registry() -> SymbolRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = SymbolRegistry(get_settings().storage_path / "symbols")
    return _default_registry


def reset_registry_for_tests() -> None:
    global _default_registry
    _default_registry = None
