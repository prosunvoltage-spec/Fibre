"""Persistiert Visualization + gerendertes Foto in DB und Dateisystem."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.enums import PhotoKind
from app.core.models import Nvt, Photo, Visualization
from app.core.repositories import AuditRepo
from app.core.schemas import (
    EnvironmentAnalysisSchema,
    VisualizationSchema,
)
from app.ruleplans import RulePlanLibrary
from app.visualization.proposer import ProposalResult, propose_visualization
from app.visualization.renderer import render_overlay

logger = logging.getLogger(__name__)


@dataclass
class VisualizeOutcome:
    nvt_id: str
    visualization_created: bool
    rendered_photo_path: str | None
    warnings: list[str] = field(default_factory=list)
    reason: str | None = None


class VisualizationBuilder:
    """Erzeugt Overlay-Modell + gerendertes Bild und schreibt beides in DB."""

    def __init__(
        self,
        session: Session,
        library: RulePlanLibrary,
        *,
        storage_root: Path,
        user: str | None = None,
    ) -> None:
        self.session = session
        self.library = library
        self.storage_root = storage_root
        self.user = user
        self._audit = AuditRepo(session)

    def build_for_nvt(self, nvt: Nvt, *, force: bool = False) -> VisualizeOutcome:
        # Voraussetzungen
        if nvt.environment is None:
            return VisualizeOutcome(
                nvt_id=str(nvt.id),
                visualization_created=False,
                rendered_photo_path=None,
                warnings=["EnvironmentAnalysis fehlt — Vision zuerst ausführen"],
            )
        if not nvt.photos:
            return VisualizeOutcome(
                nvt_id=str(nvt.id),
                visualization_created=False,
                rendered_photo_path=None,
                warnings=["Kein Foto vorhanden"],
            )
        if nvt.visualization is not None and not force:
            return VisualizeOutcome(
                nvt_id=str(nvt.id),
                visualization_created=False,
                rendered_photo_path=None,
                warnings=["Visualisierung existiert — force=true zum Überschreiben"],
            )

        base_photo = next(p for p in nvt.photos if p.kind == PhotoKind.ORIGINAL or str(p.kind) == "original")

        env_schema = self._env_to_schema(nvt.environment)
        ruleplan_entry = None
        if nvt.decision is not None and nvt.decision.selected_ruleplan_id:
            ruleplan_entry = self.library.get(nvt.decision.selected_ruleplan_id)

        proposal: ProposalResult = propose_visualization(
            nvt_id=nvt.id,
            base_photo_id=base_photo.id,
            env=env_schema,
            ruleplan=ruleplan_entry,
        )

        if not proposal.has_proposal() or proposal.visualization is None:
            self._audit.append(
                action="VISUALIZATION_SKIPPED",
                user=self.user,
                project_id=nvt.project_id,
                nvt_id=nvt.id,
                payload={"reason": proposal.reason, "warnings": proposal.warnings},
            )
            return VisualizeOutcome(
                nvt_id=str(nvt.id),
                visualization_created=False,
                rendered_photo_path=None,
                reason=proposal.reason,
                warnings=proposal.warnings,
            )

        # Rendern
        out_dir = self.storage_root / "projects" / str(nvt.project_id) / "visualizations"
        out_dir.mkdir(parents=True, exist_ok=True)
        proposal_path = out_dir / f"{nvt.id}_proposal.jpg"

        base_path = Path(base_photo.stored_path)
        render_result = render_overlay(
            base_photo_path=base_path,
            visualization=proposal.visualization,
            output_path=proposal_path,
        )

        # Foto-Row für das Proposal
        with proposal_path.open("rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()

        rendered_photo = Photo(
            nvt_id=nvt.id,
            filename=proposal_path.name,
            stored_path=str(proposal_path),
            mime_type="image/jpeg",
            width=render_result.width,
            height=render_result.height,
            sha256=sha,
            exif={},
            ocr_json=None,
            kind=PhotoKind.PROPOSAL,
        )
        nvt.photos.append(rendered_photo)
        self.session.add(rendered_photo)
        self.session.flush()

        # Alte Visualization löschen wenn force
        if nvt.visualization is not None:
            self.session.delete(nvt.visualization)
            self.session.flush()

        viz = Visualization(
            nvt_id=nvt.id,
            base_photo_id=base_photo.id,
            symbols=[s.model_dump(mode="json") for s in proposal.visualization.symbols],
            shapes=[s.model_dump(mode="json") for s in proposal.visualization.shapes],
            rendered_photo_id=rendered_photo.id,
            final_photo_id=None,
            edited_by_user=False,
            edited_at=None,
        )
        nvt.visualization = viz
        self.session.add(viz)
        self.session.flush()

        warnings = list(proposal.warnings) + list(render_result.warnings)
        self._audit.append(
            action="VISUALIZATION_CREATED",
            user=self.user,
            project_id=nvt.project_id,
            nvt_id=nvt.id,
            payload={
                "rendered_photo_id": str(rendered_photo.id),
                "symbol_count": render_result.rendered_symbol_count,
                "shape_count": render_result.rendered_shape_count,
                "warnings": warnings,
            },
        )

        return VisualizeOutcome(
            nvt_id=str(nvt.id),
            visualization_created=True,
            rendered_photo_path=str(proposal_path),
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _env_to_schema(self, env) -> EnvironmentAnalysisSchema:  # type: ignore[no-untyped-def]
        return EnvironmentAnalysisSchema(
            nvt_id=env.nvt_id,
            road_present=env.road_present,
            sidewalk_present=env.sidewalk_present,
            cycleway_present=env.cycleway_present,
            shared_cycle_footway_present=env.shared_cycle_footway_present,
            parking_lane_present=env.parking_lane_present,
            seiten_streifen_present=env.seiten_streifen_present,
            private_property=env.private_property,
            business_property=env.business_property,
            driveway_present=env.driveway_present,
            intersection_present=env.intersection_present,
            junction_present=env.junction_present,
            cul_de_sac=env.cul_de_sac,
            curve_present=env.curve_present,
            bus_stop_nearby=env.bus_stop_nearby,
            fire_access=env.fire_access,
            nvt_position=env.nvt_position,
            road_class=env.road_class,
            sidewalk_width_m=env.sidewalk_width_m,
            roadway_width_m=env.roadway_width_m,
            cycleway_width_m=env.cycleway_width_m,
            distance_nvt_to_road_m=env.distance_nvt_to_road_m,
            parked_vehicles_in_workarea=env.parked_vehicles_in_workarea,
            existing_signs=list(env.existing_signs or []),
            existing_barriers=list(env.existing_barriers or []),
            obstacles=list(env.obstacles or []),
            sight_relations_affected=env.sight_relations_affected,
            contributing_photos=[str(p) for p in (env.contributing_photos or [])],
            vision_confidence=env.vision_confidence,
            data_completeness=env.data_completeness,
            contradictions=list(env.contradictions or []),
            raw_provider_output=dict(env.raw_provider_output or {}),
            model_id=env.model_id or "",
            model_version=env.model_version,
            prompt_hash=env.prompt_hash or "",
            created_at=env.created_at,
        )
