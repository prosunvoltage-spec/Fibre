.PHONY: help venv install install-dev clean migrate revision downgrade dev test test-fast lint format typecheck seed sample check

PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin
PIP    := $(BIN)/pip
PYTEST := $(BIN)/pytest
ALEMBIC := $(BIN)/alembic
UVICORN := $(BIN)/uvicorn

help:  ## Zeige verfügbare Targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

venv:  ## Virtuelles Environment anlegen (.venv)
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

install: venv  ## Runtime-Deps installieren
	$(PIP) install -e .

install-dev: venv  ## Runtime + Dev-Deps installieren
	$(PIP) install -e ".[dev]"

clean:  ## Caches und Build-Artefakte löschen
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

migrate:  ## Alle DB-Migrationen anwenden
	$(ALEMBIC) upgrade head

revision:  ## Neue Alembic-Migration (M="beschreibung")
	@if [ -z "$(M)" ]; then echo "Nutze: make revision M=\"kurze beschreibung\""; exit 1; fi
	$(ALEMBIC) revision --autogenerate -m "$(M)"

downgrade:  ## Letzte Migration zurücknehmen
	$(ALEMBIC) downgrade -1

dev:  ## Backend im Reload-Modus starten
	$(UVICORN) app.main:app --reload --host 127.0.0.1 --port 8000

test:  ## Alle Tests laufen lassen
	$(PYTEST)

test-fast:  ## Nur schnelle Unit-Tests (ohne integration/regression)
	$(PYTEST) -m "not integration and not regression"

lint:  ## Ruff-Lint
	$(BIN)/ruff check .

format:  ## Ruff-Format
	$(BIN)/ruff format .

typecheck:  ## Mypy
	$(BIN)/mypy app

check: lint typecheck test  ## Lint + Typecheck + Tests

sample:  ## Beispiel-Projekt + NVT in DB anlegen
	$(BIN)/python scripts/create_sample_project.py
