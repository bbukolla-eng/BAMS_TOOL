# Follow-ups (deferred to Phase 2+)

## Backend
- Project-level integration tests for full CRUD (unit tests for the calculator
  arithmetic exist and are passing; full FastAPI integration tests require an
  async Postgres test container). Placeholder file:
  `tests/test_phase1_integration.py` documents what should be added.
- Retire or repurpose `BidSummarySection` table — currently unused after the
  trade-rollup endpoint was switched to compute-on-demand.
- Add labor_rate lookup to the bid calculate pipeline so a project region can
  retroactively rate-update older bids (currently only new line items pick up
  the region rate).

## Frontend
- Price book inline edit (PATCH) — API is present, UI still opens a modal.
- Dark mode refinement — the toggle flips Tailwind `dark:` classes but only the
  bid/price-book pages have been audited; Drawings / Takeoff / Specs pages may
  have contrast gaps.
- Add-line picker could support debounced search server-side for > 500 items.
- Status bar polling interval (15s) should be replaced with server-sent events
  once the SSE hub extends beyond drawing jobs.

## Data
- Seed 100 mechanical items is currently 110 items across duct/VRF/DOAS/
  piping/insulation/diffusers/VAV/controls/equipment. Short of a "BOM-quality"
  set for some sub-categories (e.g., spiral fittings) — track in seed data
  review.
- Regional multipliers are RSMeans-style approximations; replace with a
  licensed feed in production.

## AI (Phase 2 scope — not started)
- Anthropic client wrapper
- Prompt versioned markdown files
- `estimate_line_items.md`, `takeoff_review.md`, `spec_extraction.md`,
  `spec_conflict_check.md`, `qa_anomaly_detection.md`, `missing_scope.md`,
  `labor_hour_sanity.md`
