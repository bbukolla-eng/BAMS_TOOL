"""Upgrade spec_sections.embedding from ARRAY(Float) to vector(768).

pgvector distance operators (<=> cosine, <-> L2) require the native vector
type. The initial migration incorrectly used ARRAY(Float). This migration
drops the old column and recreates it as vector(768).

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-23
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure the pgvector extension is present (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Drop the incorrectly typed column and recreate as native vector type.
    # Existing embedding data (stored as float arrays) is lost — spec sections
    # will be re-embedded on the next processing run.
    op.execute("ALTER TABLE spec_sections DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE spec_sections ADD COLUMN embedding vector(768)")

    # Create an ivfflat index for approximate nearest-neighbour search.
    # lists=100 is a good starting point; tune for dataset size.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_spec_sections_embedding "
        "ON spec_sections USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_spec_sections_embedding")
    op.execute("ALTER TABLE spec_sections DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE spec_sections ADD COLUMN embedding float[]")
