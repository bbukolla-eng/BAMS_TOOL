"""Add fittings JSON column to material_runs.

Stores per-run fitting counts derived from the run-tracer connectivity graph:
  {"elbow_45": int, "elbow_90": int, "tee": int, "cross": int, "transition": int}

Without this we under-count installed material on every HVAC takeoff —
duct/pipe fittings are 20-30% of typical installed quantities.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "material_runs",
        sa.Column("fittings", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("material_runs", "fittings")
