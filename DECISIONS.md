# Engineering Decisions — MEP Master Platform (Phase 1)

Context: the repository already had a mature "BAMS AI" scaffold when I picked it up.
Where the build spec's nominal choices diverged from prior art, the rule was:
**extend the existing shape, don't rewrite.** Divergences are logged here.

## D-001 — Keep existing layout (`backend/modules/...`) instead of `backend/app/...`
The spec calls for `backend/app/api`, `backend/app/services`, etc. The codebase was
already organized as `backend/{api,core,models,modules,migrations,workers,ai,schemas}`
with per-module routers under `backend/modules/<name>/router.py`. Rewriting would
have broken ~40 files and multiple migrations for no user-visible gain.

## D-002 — Extend existing `PriceBookItem` instead of a parallel model
The existing model already had most fields the spec wanted. Added columns in a new
migration: `subcategory`, `equipment_unit_cost`, `material_markup_pct`,
`labor_markup_pct`, `region_code`, `source`. Trade membership is tracked via the
existing `trade_id → trades.code` (MECH / ELEC / PLMB) — no redundant column added.

## D-003 — Regional multipliers applied at bid calculate time
Each bid snapshots `regional_multiplier` when calculated, keyed on
`project.region_code`. Line items record `equipment_unit_cost` + `equipment_total`
pre-regional; the stored `line_total` already includes the multiplier. This keeps
historical bids stable even if the regional lookup table is later edited.

Formula per spec: `line_total = qty × (material + labor_hrs × labor_rate + equipment) × regional_mult`.

## D-004 — Labor rates layered: item → trade → region × category
Resolution order for a line item's labor rate:
1. Explicit `labor_rate` on the BidLineItem (if set)
2. `LaborRate` for (project.region_code, line_item.trade.labor_category)
3. Trade.base_labor_rate fallback

The 5 labor categories seeded: sheet_metal, steamfitter, plumber, electrician, laborer.

## D-005 — `Assumption`, `Exclusion`, `Alternate` as three sibling tables
Keeping them separate preserves typed semantics in the exporter (Alternates have a
cost impact; assumptions/exclusions are prose). All three are per-bid and deleted
with the bid.

## D-006 — SQLite for dev via `Base.metadata.create_all`, Postgres via Alembic
`backend/api/main.py` lifespan calls `Base.metadata.create_all` when the URL is
SQLite, so new ORM models automatically create their tables on first launch.
Alembic migrations still own the Postgres upgrade path. The new 0003 migration
targets Postgres and uses portable types (String/Float/Integer/Boolean/Text/DateTime).

## D-007 — Regional multiplier values
Numbers are the industry-standard RSMeans-style city cost index normalized so
Kansas City ≈ 1.00. NYC metro = 1.35, SF = 1.32, Boston = 1.22, Seattle = 1.18,
LA = 1.15, DC = 1.12, Chicago = 1.10. State defaults average across metros. These
are seed defaults and are user-editable in the UI (price book / regional
multipliers tab) — not a pricing source of truth.

## D-008 — Line-item costs in Phase 1 are manual or imported
No AI-assisted quantity generation in Phase 1. Phase 2 adds that. The bid editor
supports: manual add, price book picker (search and insert), and takeoff import
(existing).

## D-009 — Trade rollup implemented as a computed endpoint, not a stored table
`GET /api/bids/{id}/summary` groups line items by `trade.code` in-memory. For a
bid with < 1,000 line items (well above typical scope) this is < 1 ms and avoids
stale-cache issues. The existing `BidSummarySection` table is untouched but
unused by the new endpoint — flagged in FOLLOWUPS.md for cleanup.

## D-010 — Cost-per-SF requires `project.total_sf`
Added `total_sf` to the Project model. The summary endpoint returns
`cost_per_sf: None` if SF is not set rather than zero (distinguishes "not computed"
from "zero SF"). UI shows a dash in that case.

## D-011 — Excel export uses a single workbook with 6+ sheets
Summary / Mechanical / Electrical / Plumbing / Assumptions-Exclusions-Alternates /
Assumptions separately. Summary sheet pulls from the trade rollup endpoint logic
for consistency.

## D-012 — Pre-commit hooks: ruff-format + ruff-check + prettier
Using `ruff format` rather than `black` since the backend already uses ruff and
adding black creates double formatting. Prettier formats the frontend.
