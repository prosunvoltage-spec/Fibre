"""Persistiert Vision-Ergebnisse als EnvironmentAnalysis + steuert NVT-Status."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.enums import NvtStatus
from app.core.models import EnvironmentAnalysis, Nvt, Photo
from app.core.repositories import AuditRepo, NvtRepo
from app.vision.base import VisionInput
from app.vision.pipeline import VisionPipeline, VisionPipelineOutcome

logger = logging.getLogger(__name__)


@dataclass
class BuildOutcome:
    nvt_id: str
    status: NvtStatus
    environment_created: bool
    manual_review_required: bool
    attempts: int
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class EnvironmentBuilder:
    """Führt die Vision-Analyse für einen NVT aus und schreibt das Ergebnis in die DB."""

    def __init__(self, session: Session, pipeline: VisionPipeline, user: str | None = None) -> None:
        self.session = session
        self.pipeline = pipeline
        self.user = user
        self._nvt_repo = NvtRepo(session)
        self._audit = AuditRepo(session)

    def analyze(self, nvt: Nvt, *, force: bool = False) -> BuildOutcome:
        # Duplikat-Guard
        if nvt.environment is not None and not force:
            return BuildOutcome(
                nvt_id=str(nvt.id),
                status=NvtStatus(nvt.status),
                environment_created=False,
                manual_review_required=nvt.environment.data_completeness < 1,
                attempts=0,
                warnings=["EnvironmentAnalysis existiert bereits — force=true zum Überschreiben"],
            )

        photos: list[Photo] = [p for p in nvt.photos if p.kind == "original" or p.kind.value == "original"]  # type: ignore[union-attr]
        if not photos:
            return BuildOutcome(
                nvt_id=str(nvt.id),
                status=NvtStatus(nvt.status),
                environment_created=False,
                manual_review_required=True,
                attempts=0,
                errors=["Kein Foto für die Analyse vorhanden"],
            )

        # Status: NEW/ANALYZED → ANALYZING (soweit erlaubt)
        current = NvtStatus(nvt.status) if isinstance(nvt.status, str) else nvt.status
        if current == NvtStatus.NEW:
            self._nvt_repo.update_status(nvt, NvtStatus.ANALYZING)

        vision_inputs = [
            VisionInput(photo_path=type(photo.stored_path).__mro__[0] and _to_path(photo.stored_path),
                        photo_id=str(photo.id),
                        caption=photo.filename)
            for photo in photos
        ]

        self._audit.append(
            action="VISION_STARTED",
            user=self.user,
            project_id=nvt.project_id,
            nvt_id=nvt.id,
            payload={"photos": [str(p.id) for p in photos]},
        )

        outcome: VisionPipelineOutcome = self.pipeline.analyze(vision_inputs)

        if not outcome.is_ok() or outcome.response is None:
            self._nvt_repo.update_status(nvt, NvtStatus.NEEDS_REVIEW)
            self._audit.append(
                action="VISION_FAILED",
                user=self.user,
                project_id=nvt.project_id,
                nvt_id=nvt.id,
                payload={
                    "attempts": outcome.attempts,
                    "errors": outcome.errors,
                    "warnings": outcome.warnings,
                },
            )
            return BuildOutcome(
                nvt_id=str(nvt.id),
                status=NvtStatus.NEEDS_REVIEW,
                environment_created=False,
                manual_review_required=True,
                attempts=outcome.attempts,
                errors=outcome.errors,
                warnings=outcome.warnings,
            )

        response = outcome.response
        raw = outcome.raw_provider_response

        # Bestehendes Environment löschen (bei force=True)
        if nvt.environment is not None:
            self.session.delete(nvt.environment)
            self.session.flush()

        env = EnvironmentAnalysis(
            nvt_id=nvt.id,
            road_present=response.road_present,
            sidewalk_present=response.sidewalk_present,
            cycleway_present=response.cycleway_present,
            shared_cycle_footway_present=response.shared_cycle_footway_present,
            parking_lane_present=response.parking_lane_present,
            seiten_streifen_present=response.seiten_streifen_present,
            private_property=response.private_property,
            business_property=response.business_property,
            driveway_present=response.driveway_present,
            intersection_present=response.intersection_present,
            junction_present=response.junction_present,
            cul_de_sac=response.cul_de_sac,
            curve_present=response.curve_present,
            bus_stop_nearby=response.bus_stop_nearby,
            fire_access=response.fire_access,
            nvt_position=response.nvt_position,
            road_class=response.road_class,
            sidewalk_width_m=response.sidewalk_width_m,
            roadway_width_m=response.roadway_width_m,
            cycleway_width_m=response.cycleway_width_m,
            distance_nvt_to_road_m=response.distance_nvt_to_road_m,
            parked_vehicles_in_workarea=response.parked_vehicles_in_workarea,
            existing_signs=list(response.existing_signs),
            existing_barriers=list(response.existing_barriers),
            obstacles=list(response.obstacles),
            sight_relations_affected=response.sight_relations_affected,
            contributing_photos=[str(p.id) for p in photos],
            vision_confidence=response.vision_confidence,
            data_completeness=response.data_completeness(),
            contradictions=list(response.contradictions),
            raw_provider_output=(raw.parsed if raw and raw.parsed else {}),
            model_id=(raw.model_id if raw else ""),
            model_version=(raw.model_version if raw else None),
            prompt_hash=self.pipeline.prompt.sha256,
            created_at=datetime.now(UTC),
        )
        # Bidirektionale Zuweisung, damit nvt.environment sofort verfügbar ist
        nvt.environment = env
        self.session.add(env)
        self.session.flush()

        # Status setzen: manuelle Prüfung oder ANALYZED
        new_status = NvtStatus.NEEDS_REVIEW if outcome.manual_review_required else NvtStatus.ANALYZED
        # Übergang muss valide sein
        current = NvtStatus(nvt.status) if isinstance(nvt.status, str) else nvt.status
        if current != new_status:
            try:
                self._nvt_repo.update_status(nvt, new_status)
            except Exception as exc:
                logger.warning("Statuswechsel %s→%s abgelehnt: %s", current, new_status, exc)

        self._audit.append(
            action="VISION_COMPLETED",
            user=self.user,
            project_id=nvt.project_id,
            nvt_id=nvt.id,
            model_id=raw.model_id if raw else None,
            payload={
                "vision_confidence": float(response.vision_confidence),
                "data_completeness": float(response.data_completeness()),
                "attempts": outcome.attempts,
                "manual_review": outcome.manual_review_required,
                "input_tokens": raw.input_tokens if raw else 0,
                "output_tokens": raw.output_tokens if raw else 0,
                "prompt_hash": self.pipeline.prompt.sha256,
            },
        )

        return BuildOutcome(
            nvt_id=str(nvt.id),
            status=NvtStatus(nvt.status),
            environment_created=True,
            manual_review_required=outcome.manual_review_required,
            attempts=outcome.attempts,
            warnings=list(response.contradictions) + list(outcome.warnings),
        )


def _to_path(value):  # type: ignore[no-untyped-def]
    from pathlib import Path
    return Path(str(value))
