"""Analyze-Endpoint: startet Vision-Pipeline für einen NVT."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import DbSession, SettingsDep
from app.classification.environment_builder import EnvironmentBuilder
from app.config import Settings
from app.core.repositories import NvtRepo
from app.vision import MockVisionProvider, VisionPipeline
from app.vision.anthropic_provider import AnthropicVisionProvider
from app.vision.prompts import load_prompt

router = APIRouter(prefix="/api/projects/{project_id}/nvts/{nvt_id}/analyze", tags=["analyze"])


class AnalyzeOut(BaseModel):
    nvt_id: str
    status: str
    environment_created: bool
    manual_review_required: bool
    attempts: int
    warnings: list[str] = []
    errors: list[str] = []


@router.post("", response_model=AnalyzeOut)
def analyze_nvt(
    project_id: UUID,
    nvt_id: UUID,
    force: bool = Query(default=False, description="Bestehende Analyse überschreiben"),
    provider_override: str | None = Query(default=None, description="'mock' oder 'anthropic'"),
    user: str | None = Query(default=None),
    db: Session = DbSession,
    settings: Settings = SettingsDep,
) -> AnalyzeOut:
    nvt = NvtRepo(db).get(nvt_id)
    if nvt is None or nvt.project_id != project_id:
        raise HTTPException(status_code=404, detail="NVT nicht gefunden")

    provider_name = (provider_override or settings.vision_provider).lower()
    if provider_name == "mock":
        provider = MockVisionProvider()
    elif provider_name == "anthropic":
        provider = AnthropicVisionProvider()
        if not settings.anthropic_api_key:
            raise HTTPException(
                status_code=400,
                detail=(
                    "ANTHROPIC_API_KEY nicht gesetzt — Analyse kann nicht starten. "
                    "Nutze ?provider_override=mock für offline-Testlauf."
                ),
            )
    else:
        raise HTTPException(status_code=400, detail=f"Unbekannter Provider: {provider_name}")

    prompt = load_prompt("environment_analysis")
    pipeline = VisionPipeline(provider=provider, prompt=prompt)
    builder = EnvironmentBuilder(db, pipeline=pipeline, user=user)
    outcome = builder.analyze(nvt, force=force)

    return AnalyzeOut(
        nvt_id=outcome.nvt_id,
        status=outcome.status.value,
        environment_created=outcome.environment_created,
        manual_review_required=outcome.manual_review_required,
        attempts=outcome.attempts,
        warnings=outcome.warnings,
        errors=outcome.errors,
    )
