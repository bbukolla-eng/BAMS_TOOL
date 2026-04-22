"""Initial schema — all BAMS tables

Revision ID: 0001
Revises:
Create Date: 2026-04-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector extension (must already exist via init_db.sql)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── organizations ───────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("plan", sa.String(20), server_default="starter"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── users ───────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(20), server_default="viewer"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── trades ──────────────────────────────────────────────────────────────
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(20)),
        sa.Column("division", sa.String(10)),
        sa.Column("description", sa.Text),
        sa.Column("base_labor_rate", sa.Numeric(10, 2), server_default="0"),
        sa.Column("foreman_rate", sa.Numeric(10, 2), server_default="0"),
        sa.Column("is_primary", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── price_book_items ────────────────────────────────────────────────────
    op.create_table(
        "price_book_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_id", sa.Integer, sa.ForeignKey("trades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("csi_code", sa.String(20)),
        sa.Column("category", sa.String(50)),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("unit", sa.String(20)),
        sa.Column("size", sa.String(50)),
        sa.Column("material_unit_cost", sa.Numeric(12, 4), server_default="0"),
        sa.Column("labor_hours_per_unit", sa.Numeric(8, 4), server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── overhead_configs ────────────────────────────────────────────────────
    op.create_table(
        "overhead_configs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean, server_default="false"),
        sa.Column("fica_rate", sa.Numeric(6, 4), server_default="0.0765"),
        sa.Column("futa_rate", sa.Numeric(6, 4), server_default="0.006"),
        sa.Column("suta_rate", sa.Numeric(6, 4), server_default="0.027"),
        sa.Column("workers_comp_rate", sa.Numeric(6, 4), server_default="0.12"),
        sa.Column("general_liability_rate", sa.Numeric(6, 4), server_default="0.015"),
        sa.Column("health_insurance_rate", sa.Numeric(6, 4), server_default="0.08"),
        sa.Column("vacation_rate", sa.Numeric(6, 4), server_default="0.05"),
        sa.Column("total_burden_rate", sa.Numeric(6, 4), server_default="0.375"),
        sa.Column("general_overhead_rate", sa.Numeric(6, 4), server_default="0.10"),
        sa.Column("small_tools_rate", sa.Numeric(6, 4), server_default="0.02"),
        sa.Column("material_markup", sa.Numeric(6, 4), server_default="0.10"),
        sa.Column("profit_margin", sa.Numeric(6, 4), server_default="0.08"),
        sa.Column("contingency_rate", sa.Numeric(6, 4), server_default="0.03"),
        sa.Column("bond_rate", sa.Numeric(6, 4), server_default="0.015"),
        sa.Column("permit_rate", sa.Numeric(6, 4), server_default="0.01"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── projects ────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("address", sa.Text),
        sa.Column("status", sa.String(30), server_default="active"),
        sa.Column("project_type", sa.String(30), server_default="commercial"),
        sa.Column("bid_due_date", sa.Date),
        sa.Column("estimated_value", sa.Numeric(15, 2)),
        sa.Column("owner_name", sa.String(255)),
        sa.Column("gc_name", sa.String(255)),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── project_members ─────────────────────────────────────────────────────
    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(30), server_default="viewer"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

    # ── drawings ────────────────────────────────────────────────────────────
    op.create_table(
        "drawings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(10)),
        sa.Column("storage_key", sa.String(512)),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("discipline", sa.String(30)),
        sa.Column("sheet_number", sa.String(30)),
        sa.Column("sheet_title", sa.String(255)),
        sa.Column("revision", sa.String(20)),
        sa.Column("error_message", sa.Text),
        sa.Column("uploaded_by_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── drawing_pages ───────────────────────────────────────────────────────
    op.create_table(
        "drawing_pages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("drawing_id", sa.Integer, sa.ForeignKey("drawings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("width_ft", sa.Float),
        sa.Column("height_ft", sa.Float),
        sa.Column("scale_factor", sa.Float),
        sa.Column("scale_label", sa.String(50)),
        sa.Column("thumbnail_key", sa.String(512)),
    )

    # ── symbols ─────────────────────────────────────────────────────────────
    op.create_table(
        "symbols",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("page_id", sa.Integer, sa.ForeignKey("drawing_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol_type", sa.String(80), nullable=False),
        sa.Column("x_ft", sa.Float),
        sa.Column("y_ft", sa.Float),
        sa.Column("width_ft", sa.Float),
        sa.Column("height_ft", sa.Float),
        sa.Column("confidence", sa.Float),
        sa.Column("detection_source", sa.String(20)),
        sa.Column("csi_code", sa.String(20)),
        sa.Column("block_name", sa.String(255)),
        sa.Column("label", sa.String(255)),
        sa.Column("is_verified", sa.Boolean, server_default="false"),
        sa.Column("is_rejected", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── material_runs ───────────────────────────────────────────────────────
    op.create_table(
        "material_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("page_id", sa.Integer, sa.ForeignKey("drawing_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_type", sa.String(80), nullable=False),
        sa.Column("csi_code", sa.String(20)),
        sa.Column("layer", sa.String(255)),
        sa.Column("path_json", postgresql.JSONB),
        sa.Column("length_ft", sa.Float),
        sa.Column("size_label", sa.String(50)),
        sa.Column("is_verified", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── specifications ──────────────────────────────────────────────────────
    op.create_table(
        "specifications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("storage_key", sa.String(512)),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("division", sa.String(10)),
        sa.Column("uploaded_by_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── spec_sections ───────────────────────────────────────────────────────
    op.create_table(
        "spec_sections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("spec_id", sa.Integer, sa.ForeignKey("specifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_number", sa.String(20)),
        sa.Column("title", sa.String(512)),
        sa.Column("raw_text", sa.Text),
        sa.Column("materials", postgresql.JSONB),
        sa.Column("products", postgresql.JSONB),
        sa.Column("standards", postgresql.JSONB),
        sa.Column("installation_requirements", postgresql.JSONB),
        sa.Column("embedding", postgresql.ARRAY(sa.Float)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── takeoff_items ───────────────────────────────────────────────────────
    op.create_table(
        "takeoff_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("price_book_item_id", sa.Integer, sa.ForeignKey("price_book_items.id")),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("csi_code", sa.String(20)),
        sa.Column("category", sa.String(50)),
        sa.Column("quantity", sa.Numeric(14, 4), server_default="0"),
        sa.Column("unit", sa.String(20)),
        sa.Column("material_unit_cost", sa.Numeric(12, 4)),
        sa.Column("labor_hours_per_unit", sa.Numeric(8, 4)),
        sa.Column("is_locked", sa.Boolean, server_default="false"),
        sa.Column("confidence", sa.Float, server_default="0"),
        sa.Column("source_symbol_ids", postgresql.JSONB),
        sa.Column("source_run_ids", postgresql.JSONB),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── bids ────────────────────────────────────────────────────────────────
    op.create_table(
        "bids",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("overhead_config_id", sa.Integer, sa.ForeignKey("overhead_configs.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("total_material_cost", sa.Numeric(15, 2), server_default="0"),
        sa.Column("total_material_markup", sa.Numeric(15, 2), server_default="0"),
        sa.Column("total_labor_hours", sa.Numeric(12, 2), server_default="0"),
        sa.Column("total_labor_cost", sa.Numeric(15, 2), server_default="0"),
        sa.Column("total_burden", sa.Numeric(15, 2), server_default="0"),
        sa.Column("total_overhead", sa.Numeric(15, 2), server_default="0"),
        sa.Column("subtotal", sa.Numeric(15, 2), server_default="0"),
        sa.Column("contingency", sa.Numeric(15, 2), server_default="0"),
        sa.Column("bond", sa.Numeric(15, 2), server_default="0"),
        sa.Column("permit", sa.Numeric(15, 2), server_default="0"),
        sa.Column("profit", sa.Numeric(15, 2), server_default="0"),
        sa.Column("grand_total", sa.Numeric(15, 2), server_default="0"),
        sa.Column("notes", sa.Text),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── bid_line_items ──────────────────────────────────────────────────────
    op.create_table(
        "bid_line_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id", ondelete="CASCADE"), nullable=False),
        sa.Column("takeoff_item_id", sa.Integer, sa.ForeignKey("takeoff_items.id")),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("csi_code", sa.String(20)),
        sa.Column("category", sa.String(50)),
        sa.Column("quantity", sa.Numeric(14, 4)),
        sa.Column("unit", sa.String(20)),
        sa.Column("material_unit_cost", sa.Numeric(12, 4)),
        sa.Column("material_total", sa.Numeric(15, 2)),
        sa.Column("labor_hours_per_unit", sa.Numeric(8, 4)),
        sa.Column("total_labor_hours", sa.Numeric(12, 2)),
        sa.Column("labor_rate", sa.Numeric(10, 2)),
        sa.Column("labor_total", sa.Numeric(15, 2)),
        sa.Column("line_total", sa.Numeric(15, 2)),
    )

    # ── equipment_items ─────────────────────────────────────────────────────
    op.create_table(
        "equipment_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("tag_number", sa.String(50)),
        sa.Column("equipment_type", sa.String(80), nullable=False),
        sa.Column("manufacturer", sa.String(255)),
        sa.Column("model_number", sa.String(255)),
        sa.Column("csi_code", sa.String(20)),
        sa.Column("location", sa.String(255)),
        sa.Column("specs", postgresql.JSONB),
        sa.Column("symbol_id", sa.Integer, sa.ForeignKey("symbols.id")),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── submittals ──────────────────────────────────────────────────────────
    op.create_table(
        "submittals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("submittal_number", sa.String(50)),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("csi_section", sa.String(20)),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("revision", sa.Integer, server_default="0"),
        sa.Column("submitted_date", sa.Date),
        sa.Column("required_date", sa.Date),
        sa.Column("returned_date", sa.Date),
        sa.Column("reviewer_notes", sa.Text),
        sa.Column("storage_key", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── closeout_items ──────────────────────────────────────────────────────
    op.create_table(
        "closeout_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("item_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("equipment_tag", sa.String(50)),
        sa.Column("warranty_months", sa.Integer),
        sa.Column("warranty_start_date", sa.Date),
        sa.Column("warranty_expiry_date", sa.Date),
        sa.Column("storage_key", sa.String(512)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── proposals ───────────────────────────────────────────────────────────
    op.create_table(
        "proposals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id")),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("cover_letter", sa.Text),
        sa.Column("scope_of_work", sa.Text),
        sa.Column("exclusions", sa.Text),
        sa.Column("storage_key", sa.String(512)),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── feedback_events ─────────────────────────────────────────────────────
    op.create_table(
        "feedback_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("drawing_id", sa.Integer, sa.ForeignKey("drawings.id")),
        sa.Column("page_number", sa.Integer),
        sa.Column("before_state", postgresql.JSONB),
        sa.Column("after_state", postgresql.JSONB),
        sa.Column("image_crop_path", sa.String(512)),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── ml_training_jobs ────────────────────────────────────────────────────
    op.create_table(
        "ml_training_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("model_type", sa.String(30)),
        sa.Column("dataset_size", sa.Integer),
        sa.Column("baseline_map50", sa.Float),
        sa.Column("new_map50", sa.Float),
        sa.Column("was_promoted", sa.Boolean, server_default="false"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in [
        "ml_training_jobs", "feedback_events", "proposals", "closeout_items",
        "submittals", "equipment_items", "bid_line_items", "bids",
        "takeoff_items", "spec_sections", "specifications",
        "material_runs", "symbols", "drawing_pages", "drawings",
        "project_members", "projects", "overhead_configs",
        "price_book_items", "trades", "users", "organizations",
    ]:
        op.drop_table(table)
