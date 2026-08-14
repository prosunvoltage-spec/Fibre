"""Vision-Pipeline: Fotos → strukturierte Umgebungsbeobachtung.

Kernprinzip: KI liefert Beobachtungen, keine Entscheidungen. Die Rule Engine
(Phase 6) wählt anschließend deterministisch den Regelplan.
"""

from app.vision.aggregator import aggregate_multi_photo
from app.vision.base import ProviderResponse, VisionInput, VisionProvider
from app.vision.mock_provider import MockVisionProvider
from app.vision.pipeline import VisionPipeline, VisionPipelineOutcome
from app.vision.schema import VisionEnvironmentResponse

__all__ = [
    "MockVisionProvider",
    "ProviderResponse",
    "VisionEnvironmentResponse",
    "VisionInput",
    "VisionPipeline",
    "VisionPipelineOutcome",
    "VisionProvider",
    "aggregate_multi_photo",
]
