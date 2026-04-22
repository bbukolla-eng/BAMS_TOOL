# BAMS_TOOL — BAMS AI

AI-powered MEP construction management platform: project management, automated takeoff, spec reading, bidding, and drawing analysis. Primary focus: **Division 23 (Mechanical/HVAC)**.

## Capabilities

- **Drawings AI** — Automated symbol detection and material run tracing from PDF, DWG, and DXF drawings
- **Takeoff** — Quantity takeoff from drawings with 90-99% accuracy target
- **Spec Reader** — Parse specifications, link to drawing elements, track requirements
- **Bidding Engine** — Generate bids from takeoff data with material costs and labor assemblies
- **Price Book** — Material and labor pricing database (pre-seeded for Division 23)
- **Trades** — Multi-trade support with Division 23 HVAC as primary
- **Overhead** — Configurable overhead, markup, and burden calculations
- **Submittals** — Submittal log tracking and approval workflow
- **Closeout** — O&M manuals, warranties, as-builts, punch lists
- **Proposals** — Professional proposal document generation
- **Bid Summary** — Structured summaries by trade, system, and phase
- **Equipment** — Equipment schedules with drawing location tracking
- **Self-Learning** — Continuous accuracy improvement via feedback loops

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.11 + FastAPI + SQLAlchemy 2 |
| Database | PostgreSQL 16 + pgvector + Redis |
| File Storage | MinIO (S3-compatible) |
| Task Queue | Celery 5 |
| Drawing Processing | PyMuPDF + ezdxf + OpenCV |
| Symbol Detection | YOLOv8 (Ultralytics) |
| LLM / Spec AI | Anthropic Claude API |
| Embeddings | sentence-transformers + pgvector |
| Frontend | React 18 + TypeScript + Vite |
| Desktop | Electron |
| Drawing Viewer | OpenLayers + Fabric.js |

## Quick Start

```bash
cp .env.example .env
# Edit .env — Anthropic API key required

make setup      # Install dependencies, init DB
make dev        # Start all services
make seed       # Seed price book and Division 23 data
```

App: http://localhost:3000 | API docs: http://localhost:8000/docs

## Division 23 Coverage

HVAC systems supported:
- Ductwork (supply, return, exhaust, OA) — rectangular, round, oval
- Piping — chilled water, hot water, condenser water, steam, condensate, refrigerant
- Equipment — AHUs, FCUs, VAV boxes, diffusers, fans, boilers, chillers, cooling towers, VRF
- Controls — thermostats, dampers, actuators, sensors, VFDs
- Insulation — duct and pipe insulation per spec
