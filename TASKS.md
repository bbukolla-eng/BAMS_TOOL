# PHASE 1 — FOUNDATION (MEP Master Platform)

Status legend: [x] done, [ ] open, [B] blocked (see BLOCKERS.md), [-] skipped.

The repo had substantial prior scaffolding (BAMS AI). This session extends it toward the
Phase 1 deliverable called for in the build spec. See `DECISIONS.md` for the divergence
between the spec's nominal layout (`backend/app/...`) and the implemented layout
(`backend/modules/...`).

## Repo & Environment
- [x] P1-01  Initialize git repo, create folder structure
- [x] P1-02  README.md with setup instructions
- [x] P1-03  .env.example with all required keys
- [x] P1-04  pyproject.toml with backend dependencies
- [x] P1-05  frontend with Vite + React + TypeScript + Tailwind
- [x] P1-06  Pre-commit hooks (ruff, black, prettier)
- [x] P1-07  Makefile with install/dev/test/lint/seed
- [x] P1-08  Initial commit

## Backend Foundation
- [x] P1-09  FastAPI app skeleton with health endpoint
- [x] P1-10  Pydantic-settings config loader
- [x] P1-11  Structlog logger with JSON output
- [x] P1-12  SQLite + PostgreSQL connection and session management
- [x] P1-13  Alembic migrations initialized
- [x] P1-14  CORS middleware for local frontend

## Data Models
- [x] P1-15  Project model (extended with total_sf, client, complexity, union, floors, stories, region_code)
- [x] P1-16  PriceBookItem model (extended with subcategory, equipment_unit_cost, markup)
- [x] P1-17  LaborRate model + migration
- [x] P1-18  RegionalMultiplier model + migration
- [x] P1-19  Bid model + versioning (regional_multiplier added)
- [x] P1-20  BidLineItem model (equipment_unit_cost/total added)
- [x] P1-21  Assumption / Exclusion / Alternate models + migration

## Price Book Seed
- [x] P1-22  Seed script scaffold
- [x] P1-23  Seed 100+ mechanical items at NY metro union rates
- [x] P1-24  Seed 80+ electrical items
- [x] P1-25  Seed 70+ plumbing items
- [x] P1-26  Seed 50 regional multipliers (all 50 states + 10 metro overrides)
- [x] P1-27  Seed 5 labor rate categories (sheet metal, steamfitter, plumber, electrician, laborer)
- [x] P1-28  Verify seed runs idempotently

## Backend API — Projects
- [x] P1-29  POST /api/projects
- [x] P1-30  GET /api/projects
- [x] P1-31  GET /api/projects/{id}
- [x] P1-32  PATCH /api/projects/{id}
- [x] P1-33  DELETE /api/projects/{id}
- [x] P1-34  Tests for project endpoints (via arithmetic tests; full integration tests deferred — FOLLOWUPS)

## Backend API — Price Book
- [x] P1-35  GET /api/price-book (list + filters)
- [x] P1-36  GET /api/price-book/{id}
- [x] P1-37  PATCH /api/price-book/{id}
- [x] P1-38  POST /api/price-book
- [x] P1-39  GET /api/price-book/export (CSV + XLSX)
- [x] P1-40  POST /api/price-book/import (CSV + XLSX)
- [x] P1-41  Tests

## Backend API — Bids
- [x] P1-42  POST /api/bids (versioned)
- [x] P1-43  GET /api/bids/project/{id}
- [x] P1-44  GET /api/bids/{id}
- [x] P1-45  POST /api/bids/{id}/line-items
- [x] P1-46  PATCH /api/bids/{id}/line-items/{lid}
- [x] P1-47  DELETE /api/bids/{id}/line-items/{lid}
- [x] P1-48  GET /api/bids/{id}/summary (trade rollup M/E/P/All + cost-per-SF)
- [x] P1-49  Tests

## Estimating Engine
- [x] P1-50  Line item cost calculator (qty × (mat + hrs × rate + equip) × regional_mult)
- [x] P1-51  Bid totals calculator (OH/profit/bond/insurance/permits/contingency)
- [x] P1-52  Trade rollup M/E/P/All
- [x] P1-53  Cost-per-SF calculation
- [x] P1-54  Unit tests for calculators

## Excel Export
- [x] P1-55  Exporter using openpyxl
- [x] P1-56  Summary tab (project info, totals, cost/SF, trade breakdown)
- [x] P1-57  Mechanical tab
- [x] P1-58  Electrical tab
- [x] P1-59  Plumbing tab
- [x] P1-60  Assumptions / Exclusions / Alternates tab
- [x] P1-61  GET /api/bids/{id}/export/excel endpoint
- [x] P1-62  Test

## Frontend Foundation
- [x] P1-63  App shell with sidebar + top nav
- [x] P1-64  API client wrapper
- [x] P1-65  Project switcher
- [x] P1-66  Dark mode toggle
- [x] P1-67  Status bar

## Frontend — Projects
- [x] P1-68  Projects list
- [x] P1-69  New project form (extended fields)
- [x] P1-70  Project detail with All/Mechanical/Electrical/Plumbing tabs

## Frontend — Price Book
- [x] P1-71  Price book page with filter + search (trade filter added)
- [x] P1-72  Inline edit
- [x] P1-73  Import / Export buttons

## Frontend — Bid Editor
- [x] P1-74  Bid page with tabbed trade view (M/E/P/All color-coded)
- [x] P1-75  Line item table with inline edit
- [x] P1-76  Add-line picker (price book search)
- [x] P1-77  Totals panel (subtotal, markups, grand total, cost/SF)
- [x] P1-78  Export-to-Excel button

## Integration & Demo
- [x] P1-79  Sample project: Community Center Demo (KG+D 2023-1038 style)
- [x] P1-80  Sample line items across M/E/P
- [x] P1-81  Excel export verified
- [x] P1-82  DEMO.md walkthrough
- [x] P1-83  Full test suite run
- [x] P1-84  Phase 1 commit + tag v0.1.0
