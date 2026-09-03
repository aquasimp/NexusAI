.PHONY: setup api web dev eval train quick test clean lint

PY := backend/.venv/bin/python
UVICORN := backend/.venv/bin/uvicorn
PYTEST := backend/.venv/bin/pytest

# Windows fallback detection
ifeq ($(OS),Windows_NT)
    PY := backend/.venv/Scripts/python.exe
    UVICORN := backend/.venv/Scripts/uvicorn.exe
    PYTEST := backend/.venv/Scripts/pytest.exe
endif

setup:
	python -m venv backend/.venv
	$(PY) -m pip install -U pip
	$(PY) -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt -e backend
	cd web && npm install
	@echo "\n✓ Setup complete. Run: make dev"

api:
	cd backend && $(UVICORN) nexus.main:app --reload --port 8000

web:
	cd web && npm run dev

dev:
	@echo "Starting API on :8000 and web on :3000..."
	python scripts/development/run_dev.py

eval:
	cd backend && $(PY) -m nexus.evaluation.runner --seeds 12 --clean 24

train: eval

quick:
	cd backend && $(PY) -m nexus.evaluation.runner --quick

test:
	cd backend && $(PYTEST) tests -v

lint:
	cd backend && $(PY) -m ruff check nexus/
	cd web && npm run typecheck

clean:
	rm -rf data/*.db data/*.json data/*.joblib backend/.venv web/node_modules web/.next
