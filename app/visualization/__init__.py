"""Absicherungs-Visualisierung: Overlay-Modell → gerendertes PNG auf Foto."""

from app.visualization.proposer import ProposalResult, propose_visualization
from app.visualization.renderer import RenderError, render_overlay
from app.visualization.symbols import SymbolRegistry, get_symbol_registry

__all__ = [
    "ProposalResult",
    "RenderError",
    "SymbolRegistry",
    "get_symbol_registry",
    "propose_visualization",
    "render_overlay",
]
