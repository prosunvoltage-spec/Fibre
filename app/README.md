# VRA-NVT-Automation

Backend-Package für die teil-automatisierte Erstellung technischer Unterlagen
für verkehrsrechtliche Anordnungen bei Glasfaser-Einblasarbeiten an
Netzverteilerschränken.

## Doku

Alle Grundlagendokumente liegen in `/docs/`:

- **`PROJECT_PLAN.md`** — Meilensteine, Phasen, Abnahmekriterien
- **`ARCHITECTURE.md`** — Systemarchitektur, Tech-Stack, Verzeichnisse
- **`DATA_MODEL.md`** — Alle Entities (Project, NVT, Photo, …)
- **`RULE_ENGINE.md`** — Deterministische Regelplan-Auswahl
- **`AI_PIPELINE.md`** — Vision-Provider, Prompts, Halluzinations-Schutz
- **`REVIEW_PROCESS.md`** — State-Machine, UI, Audit-Log
- **`REFERENCE_CASES.md`** — 25 NVT aus Roxel-VRA als Referenz

## Schnellstart

```bash
# 1. Env-Datei anlegen
cp .env.example .env
# 2. Dependencies installieren
make install-dev
# 3. DB anlegen
make migrate
# 4. Beispiel-Projekt anlegen
make sample
# 5. Tests
make test
# 6. API starten
make dev   # http://127.0.0.1:8000/docs
```

## Aktueller Stand

**Phase 2 — Datenmodell & Persistenz.** Enums, Pydantic-Schemas,
SQLAlchemy-Modelle, Alembic-Migrationen, Repositories, Tests.

Kein Vision, kein OCR, keine API-Routen — die kommen in Phase 4/5.
