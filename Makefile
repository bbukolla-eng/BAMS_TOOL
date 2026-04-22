.PHONY: setup dev stop seed migrate test lint format first-run

setup:
	@echo "Setting up BAMS AI..."
	cp -n .env.example .env || true
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install
	docker compose up -d postgres redis minio
	@sleep 5
	cd backend && alembic upgrade head
	python scripts/create_minio_bucket.py
	@echo "Setup complete. Run 'make seed' to load Division 23 data."

first-run: setup seed
	@echo ""
	@echo "BAMS AI is ready."
	@echo "Run 'make dev' to start all services."
	@echo "Login: admin@bams.local / Admin1234!"

dev:
	docker compose up --build

dev-backend:
	cd backend && uvicorn api.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

stop:
	docker compose down

seed:
	cd backend && python ../scripts/seed_users.py
	cd backend && python ../scripts/seed_div23_data.py

migrate:
	cd backend && alembic upgrade head

migration:
	cd backend && alembic revision --autogenerate -m "$(MSG)"

test:
	cd backend && pytest tests/ -v --cov=. --cov-report=term-missing

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format

build-frontend:
	cd frontend && npm run build

build-desktop:
	cd frontend && npm run build
	cd desktop && npm run build

docker-build:
	docker compose build

logs:
	docker compose logs -f

db-shell:
	docker compose exec postgres psql -U bams -d bams

redis-cli:
	docker compose exec redis redis-cli
