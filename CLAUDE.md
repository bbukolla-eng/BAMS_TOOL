# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

BAMS AI — MEP construction management platform focused on **Division 23 (Mechanical/HVAC)**. It ingests construction drawings (PDF / DXF / DWG / raster) and specs, automates symbol detection and material run tracing, generates quantity takeoffs, prices them against a seeded price book, and produces bids/proposals/submittals/closeout docs. There is also a self-learning loop: user corrections feed `FeedbackEvent` rows that drive weekly model retraining.

The same backend can run in two modes:
- **Server** (Docker): Postgres + Redis + MinIO + Celery workers.
- **Desktop** (Electron, `desktop/src/main.ts`): the Electron main process spawns `uvicorn api.main:app` on port 8765 as a child process, with `DATABASE_URL=sqlite+aiosqlite://...` and `STORAGE_BACKEND=local`. The React frontend detects this via `window.bamsElectron` (`frontend/src/api/client.ts`) and rewrites its `baseURL`.

Keep both modes working when changing infra: avoid Postgres-only SQL, MinIO-only storage calls, or hard dependencies on Celery workers.

## Common commands

All routine commands go through the root `Makefile`:

```bash
make first-run      # setup + seed (one-time)
make setup          # install deps, start postgres/redis/minio, alembic upgrade
make seed           # seed users + Division 23 price book
make dev            # docker compose up --build (full stack)
make dev-backend    # uvicorn api.main:app --reload --port 8000  (host)
make dev-frontend   # vite dev server on :3000                   (host)
make stop           # docker compose down
make logs           # docker compose logs -f
make db-shell       # psql into the postgres container
make redis-cli
make migrate                      # alembic upgrade head
make migration MSG="add foo"      # alembic revision --autogenerate
make lint                         # ruff check + eslint
make format                       # ruff format + prettier
make build-frontend               # tsc && vite build
make build-desktop                # builds frontend then electron
```

Default login after `make seed`: `admin@bams.local / Admin1234!`. App: http://localhost:3000 (or :5173 in `dev` profile), API docs: http://localhost:8000/docs.

### Tests

Tests live at the **repo root** in `tests/` (not under `backend/tests/`). Each test file does `sys.path.insert(0, .../backend)` so it can import backend modules without installing the package. Run them from the repo root, the way CI does:

```bash
pytest tests/ -v --tb=short                                          # all
pytest tests/test_drawing_parser/test_layer_classifier.py -v         # one file
pytest tests/test_drawing_parser/test_layer_classifier.py::TestClassifyLayerFromName::test_exact_aia_supply_duct -v
```

Note: `make test` runs `cd backend && pytest tests/ ...`, which targets `backend/tests/` — that directory does not exist. Prefer running pytest from the repo root, matching `.github/workflows/ci.yml`. Tests are designed to avoid heavy ML deps (e.g. `test_pdf_extractor.py` duplicates pure helpers rather than importing PyMuPDF) so the CI install is minimal: `pytest openpyxl python-jose[cryptography] passlib[bcrypt]`.

`pytest.ini_options` is in `backend/pyproject.toml` with `asyncio_mode = "auto"` — `async def` tests do not need an explicit marker.

### Lint

CI lint command excludes the venv and migrations:

```bash
ruff check backend/ --exclude backend/.venv --exclude backend/migrations
```

Ruff config (`backend/pyproject.toml`) intentionally ignores: `B008` (FastAPI `Depends()` default args), `E501` (line length), `E402` (post-`lifespan` imports), `F821` (SQLAlchemy forward refs), `UP042`. Don't try to "fix" these patterns.

## Architecture

### Backend layout (`backend/`)

```
api/main.py             FastAPI app, CORS, lifespan, mounts every module router under settings.api_prefix (default /api/v1) and exposes /health and the SSE /jobs/{job_key}/progress stream.
core/                   config (pydantic-settings), database (async SQLAlchemy), deps (auth), security (JWT), storage, redis_client, celery_app, exceptions, email.
models/                 SQLAlchemy 2 declarative models. Every model is re-exported from models/__init__.py — Alembic's env.py imports `models` to populate metadata, so new models MUST be added there or migrations won't see them.
modules/<feature>/      Per-feature FastAPI routers (auth, projects, drawings, drawings_ai, specs, takeoff, price_book, trades, overhead, bidding, proposals, submittals, closeout, equipment). Each is mounted at /api/v1/<feature> in api/main.py. New features follow this same pattern.
ai/                     Drawing/spec analysis pipeline. drawing_analyzer.analyze_drawing() is the dispatch entry point. Sub-extractors: pdf_extractor (PyMuPDF), dxf_extractor (ezdxf), raster_analyzer (OpenCV+EasyOCR). Then run_tracer traces material runs from vector geometry; symbol_detector runs YOLOv8 + rule-based detection. layer_classifier maps CAD layer names (AIA / abbreviated / colored) to material types. div23/symbols.py is the Division 23 symbol catalog.
workers/                Celery tasks: process_drawing, process_spec, run_takeoff, generate_proposal, train_model. Registered in core/celery_app.py `include`. Beat schedule lives there too (weekly retrain Sun 2AM, accuracy report Mon 8AM).
migrations/             Alembic. env.py imports `models` for autogenerate. `make migration MSG=...` to add one.
```

### Drawing processing pipeline (the most important flow)

1. `POST /api/v1/drawings/project/{project_id}` (`modules/drawings/router.py`) uploads file → `core.storage.upload_file` → creates `Drawing` row → tries `process_drawing_task.delay(...)`. **If Celery is unavailable it falls back to `asyncio.create_task(_run_pipeline(...))` inline.** Preserve that fallback when editing — it's what makes the Electron build work without Redis.
2. `workers/process_drawing.py::_process_drawing_async` downloads bytes, runs ODA `OdaFileConverter` for DWG→DXF, then `ai.drawing_analyzer.analyze_drawing()`.
3. `analyze_drawing` dispatches by `file_type` (pdf / dxf|dwg / image) into the matching extractor, then runs `run_tracer.trace_material_runs` and `symbol_detector.detect_symbols` per page, returning `AnalysisResult`s with **all coordinates already converted to real-world feet**.
4. The worker upserts `DrawingPage`, `Symbol`, `MaterialRun` rows and sets `Drawing.processing_status`.
5. Throughout, `_publish_progress(drawing_id, stage, pct)` publishes JSON to the Redis channel `job:drawing:{id}` and stores final status under `job_status:drawing:{id}`. The frontend subscribes via the SSE endpoint `/api/v1/jobs/{job_key}/progress` (`api/main.py`). Job keys are always `<entity>:<id>` (e.g. `drawing:42`, `spec:7`).

### Self-learning loop

User corrections (`drawings_ai/router.py::correct_symbol`, `correct_run`) (a) flip `is_verified=True` + set `verified_by_id`, and (b) write a `FeedbackEvent` with `before_state` / `after_state`. The Celery beat task `workers.train_model.check_and_retrain` consumes these. When changing the correction endpoints keep both effects in sync — the training pipeline relies on the `FeedbackEvent` shape.

### Database engine modes (`core/database.py`)

The async engine is built three different ways depending on environment, and this matters:
- `sqlite` in `DATABASE_URL` → `StaticPool`, `check_same_thread=False`. Used by Electron and tests.
- `CELERY_WORKER_RUNNING=1` → `NullPool` (every task gets a fresh connection). This avoids asyncio event-loop cross-contamination between Celery tasks; do not "optimize" by sharing the pool.
- Otherwise → pooled (`pool_size=10, max_overflow=20`).

Use `AsyncSessionLocal()` directly inside Celery tasks (`workers/process_drawing.py` is the canonical example) and `Depends(get_db)` in API routes.

### Storage (`core/storage.py`)

`upload_file` / `download_file` / `get_presigned_url` / `delete_file` / `build_object_key` abstract MinIO and local-filesystem backends. `_use_local()` is true when `settings.storage_backend == "local"` or `STORAGE_BACKEND=local` is in env (the Electron path). In local mode `get_presigned_url` returns `/api/v1/storage/{object_key}`, served by the catch-all in `api/main.py`. Always go through this module — never call MinIO or open files directly from feature code.

Object keys follow `projects/{project_id}/{category}/{filename}` (`build_object_key`).

### Auth

JWT bearer via `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")`. Use the dependencies in `core/deps.py`: `get_current_user`, `require_admin`, `require_estimator_or_admin`. Roles are the `UserRole` enum on `User`. The frontend axios client (`frontend/src/api/client.ts`) handles 401 by calling `POST /api/v1/auth/refresh` with the stored `refresh_token`, replaying the original request, and only logging out if refresh fails — preserve that interceptor behavior when touching auth.

### Frontend (`frontend/`)

Vite + React 18 + TypeScript. Path alias `@/*` → `src/*` (see `tsconfig.json`, `vite.config.ts`). State: zustand (`src/stores/auth.ts`). Server cache: `@tanstack/react-query`. Forms: react-hook-form + zod. UI: Tailwind + Radix primitives. Drawing viewer: OpenLayers + Fabric.js. Routes are declared in `src/App.tsx` and almost all are nested under `RequireAuth`.

When adding a backend module, the typical frontend touchpoints are: a page in `src/pages/`, a route in `src/App.tsx`, and API calls through the shared `api` axios instance from `src/api/client.ts` (do not create new axios instances — you'd lose the auth interceptor).

### Domain conventions

- **All drawing coordinates in the DB are real-world feet**, not pixels (`models/drawing.py` Symbol/MaterialRun, `ExtractedGeometry.scale_factor` is pixels-per-foot used during extraction). Tests and code that introduce new geometry must convert to feet before persisting.
- **Material type slugs** are canonical and must match `ai/layer_classifier.py`: `duct_supply`, `duct_return`, `duct_exhaust`, `pipe_chw_supply`, `pipe_chw_return`, `pipe_hw_supply`, `pipe_hw_return`, etc. Don't invent new variants without updating the classifier and seeded price book.
- **Disciplines** come from the `DrawingDiscipline` enum (`mechanical` is default for Division 23).
- **Detection sources** are tracked on every Symbol/MaterialRun (`yolo` | `rule` | `manual` | `vector`) — keep this populated when adding new detection paths so the accuracy report stays meaningful.

## CI

`.github/workflows/ci.yml` runs three jobs on push to `main` or `claude/**` and on PRs to `main`:
1. **test** — `pytest tests/ -v --tb=short` from repo root.
2. **lint** — ruff on `backend/` (excluding `.venv`, `migrations`).
3. **typecheck** — `npx tsc --noEmit` in `frontend/`.

Match these locally before pushing.
