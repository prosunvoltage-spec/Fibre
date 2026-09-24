"""Zentrale Konfiguration via Pydantic-Settings + .env-Datei."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Alle konfigurierbaren Werte des Systems.

    Werte werden aus Environment-Variablen und aus einer optionalen
    ``.env``-Datei im Repo-Root gelesen. Ein Beispiel liegt in
    ``.env.example``.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- DB ------------------------------------------------------------
    database_url: str = Field(default="sqlite:///./data/dev.db")

    # --- Vision --------------------------------------------------------
    vision_provider: str = "anthropic"
    vision_model: str = "claude-opus-4-7"
    anthropic_api_key: str | None = None
    vision_max_concurrency: int = 4

    # --- OCR -----------------------------------------------------------
    ocr_provider: str = "tesseract"
    tesseract_cmd: str | None = None

    # --- Geo -----------------------------------------------------------
    geo_provider: str = "nominatim"
    nominatim_user_agent: str = "vra-nvt-automation/0.1"

    # --- Storage -------------------------------------------------------
    storage_path: Path = PROJECT_ROOT / "data"
    knowledge_path: Path = PROJECT_ROOT / "knowledge"
    prompts_path: Path = PROJECT_ROOT / "prompts"

    # --- API -----------------------------------------------------------
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    secret_key: str = "change-me-development-only"

    # --- Review --------------------------------------------------------
    require_second_review: bool = False

    # --- Rule Engine Schwellwerte -------------------------------------
    rule_auto_approve_rule_conf: Decimal = Decimal("0.9")
    rule_auto_approve_completeness: Decimal = Decimal("0.9")
    rule_critical_completeness: Decimal = Decimal("0.5")
    rule_tie_threshold: Decimal = Decimal("0.05")

    # --- Regelwerks-Version -------------------------------------------
    current_ruleset_version: str = "v1"


_cached_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached Settings-Singleton (Dependency-Injection-freundlich)."""
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = Settings()
    return _cached_settings


def reload_settings() -> Settings:
    """Für Tests: Settings-Cache leeren und neu laden."""
    global _cached_settings
    _cached_settings = None
    return get_settings()
