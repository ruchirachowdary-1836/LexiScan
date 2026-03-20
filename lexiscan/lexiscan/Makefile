# LexiScan Makefile

.PHONY: install setup backend frontend test lint clean docker-up docker-down

# ── Setup ─────────────────────────────────────────────────────
install:
	pip install -r requirements.txt
	python -m spacy download en_core_web_sm

setup: install
	cp -n .env.example .env || true
	python scripts/init_db.py
	python scripts/download_models.py

# ── Run ───────────────────────────────────────────────────────
backend:
	uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	streamlit run frontend/app.py --server.port 8501

# Run both (requires GNU parallel or two terminals)
run:
	@echo "Start backend: make backend"
	@echo "Start frontend: make frontend"

# ── Testing ───────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=backend --cov-report=html --cov-report=term-missing

# ── Linting ───────────────────────────────────────────────────
lint:
	black backend/ frontend/ tests/ --check
	isort backend/ frontend/ tests/ --check-only
	flake8 backend/ frontend/ tests/ --max-line-length=100

format:
	black backend/ frontend/ tests/
	isort backend/ frontend/ tests/

# ── Docker ────────────────────────────────────────────────────
docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# ── Cleanup ───────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage 2>/dev/null || true
	@echo "Cleaned."

# ── DB ────────────────────────────────────────────────────────
db-init:
	python scripts/init_db.py

# ── Help ──────────────────────────────────────────────────────
help:
	@echo "LexiScan Makefile Commands:"
	@echo "  make install      Install Python dependencies + spaCy"
	@echo "  make setup        Full first-time setup (install + DB + models)"
	@echo "  make backend      Start FastAPI backend (port 8000)"
	@echo "  make frontend     Start Streamlit frontend (port 8501)"
	@echo "  make test         Run test suite"
	@echo "  make test-cov     Run tests with coverage report"
	@echo "  make lint         Check code style"
	@echo "  make format       Auto-format code"
	@echo "  make docker-up    Start all services with Docker Compose"
	@echo "  make docker-down  Stop Docker services"
	@echo "  make clean        Remove Python cache files"
