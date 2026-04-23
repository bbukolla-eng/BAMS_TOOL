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
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

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

    op.create_table(
        "trades",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(20)),
        sa.Column("division", sa.String(10)),
        sa.Column("description", sa.Text),
        sa.Column("base_labor_rate", sa.Float, server_default="0"),
        sa.Column("foreman_rate", sa.Float, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_primary", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "price_book_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_id", sa.Integer, sa.ForeignKey("trades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("csi_code", sa.String(20)),
        sa.Column("category", sa.String(50)),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("manufacturer", sa.String(255)),
        sa.Column("model_number", sa.String(255)),
        sa.Column("size", sa.String(50)),
        sa.Column("unit", sa.String(20)),
        sa.Column("material_unit_cost", sa.Float, server_default="0"),
        sa.Column("labor_hours_per_unit", sa.Float, server_default="0"),
        sa.Column("labor_rate", sa.Float, server_default="0"),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_price_update", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "labor_assemblies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_id", sa.Integer, sa.ForeignKey("trades.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("unit_of_measure", sa.String(50)),
        sa.Column("hours_per_unit", sa.Float),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "overhead_configs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean, server_default="false"),
        sa.Column("fica_rate", sa.Float, server_default="0.0765"),
        sa.Column("futa_rate", sa.Float, server_default="0.006"),
        sa.Column("suta_rate", sa.Float, server_default="0.027"),
        sa.Column("workers_comp_rate", sa.Float, server_default="0.12"),
        sa.Column("general_liability_rate", sa.Float, server_default="0.015"),
        sa.Column("health_insurance_rate", sa.Float, server_default="0.08"),
        sa.Column("vacation_rate", sa.Float, server_default="0.05"),
        sa.Column("total_burden_rate", sa.Float, server_default="0.375"),
        sa.Column("general_overhead_rate", sa.Float, server_default="0.10"),
        sa.Column("small_tools_rate", sa.Float, server_default="0.02"),
        sa.Column("material_markup", sa.Float, server_default="0.10"),
        sa.Column("profit_margin", sa.Float, server_default="0.08"),
        sa.Column("contingency_rate", sa.Float, server_default="0.03"),
        sa.Column("bond_rate", sa.Float, server_default="0.015"),
        sa.Column("permit_rate", sa.Float, server_default="0.01"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("project_number", sa.String(100)),
        sa.Column("project_type", sa.String(50), server_default="commercial"),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("address", sa.String(500)),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(50)),
        sa.Column("description", sa.Text),
        sa.Column("bid_due_date", sa.Date),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), server_default="member"),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignee_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.String(50), server_default="open"),
        sa.Column("priority", sa.String(50), server_default="medium"),
        sa.Column("due_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "milestones",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("due_date", sa.Date),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("is_complete", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "drawings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sheet_number", sa.String(50)),
        sa.Column("discipline", sa.String(50), server_default="mechanical"),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("file_size_bytes", sa.Integer),
        sa.Column("page_count", sa.Integer, server_default="1"),
        sa.Column("processing_status", sa.String(50), server_default="pending"),
        sa.Column("processing_error", sa.Text),
        sa.Column("celery_task_id", sa.String(255)),
        sa.Column("coord_system", sa.JSON),
        sa.Column("metadata", sa.JSON),
        sa.Column("uploaded_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "drawing_pages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("drawing_id", sa.Integer, sa.ForeignKey("drawings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("vector_extracted", sa.Boolean, server_default="false"),
        sa.Column("raster_path", sa.String(1000)),
        sa.Column("tile_manifest_path", sa.String(1000)),
        sa.Column("width_px", sa.Integer),
        sa.Column("height_px", sa.Integer),
        sa.Column("width_ft", sa.Float),
        sa.Column("height_ft", sa.Float),
        sa.Column("scale_factor", sa.Float),
        sa.Column("scale_label", sa.String(50)),
        sa.Column("geometry_data", sa.JSON),
        sa.Column("processing_status", sa.String(50), server_default="pending"),
    )

    op.create_table(
        "symbols",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("page_id", sa.Integer, sa.ForeignKey("drawing_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol_type", sa.String(100), nullable=False),
        sa.Column("x", sa.Float, nullable=False),
        sa.Column("y", sa.Float, nullable=False),
        sa.Column("width", sa.Float),
        sa.Column("height", sa.Float),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("detection_source", sa.String(50), server_default="yolo"),
        sa.Column("label", sa.String(255)),
        sa.Column("properties", sa.JSON),
        sa.Column("equipment_id", sa.Integer),  # FK added after equipment table
        sa.Column("is_verified", sa.Boolean, server_default="false"),
        sa.Column("verified_by_id", sa.Integer, sa.ForeignKey("users.id")),
    )

    op.create_table(
        "material_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("page_id", sa.Integer, sa.ForeignKey("drawing_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_type", sa.String(100), nullable=False),
        sa.Column("path", sa.JSON, nullable=False),
        sa.Column("length_ft", sa.Float, nullable=False),
        sa.Column("size", sa.String(50)),
        sa.Column("spec_reference", sa.String(255)),
        sa.Column("layer_name", sa.String(255)),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("detection_source", sa.String(50), server_default="vector"),
        sa.Column("is_verified", sa.Boolean, server_default="false"),
        sa.Column("verified_by_id", sa.Integer, sa.ForeignKey("users.id")),
    )

    op.create_table(
        "drawing_markups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("drawing_id", sa.Integer, sa.ForeignKey("drawings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer, server_default="1"),
        sa.Column("markup_type", sa.String(50)),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("color", sa.String(20)),
        sa.Column("label", sa.String(500)),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "specifications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("division", sa.String(10)),
        sa.Column("processing_status", sa.String(50), server_default="pending"),
        sa.Column("celery_task_id", sa.String(255)),
        sa.Column("uploaded_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "spec_sections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("specification_id", sa.Integer, sa.ForeignKey("specifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_number", sa.String(20)),
        sa.Column("section_title", sa.String(500)),
        sa.Column("raw_text", sa.Text),
        sa.Column("structured_data", sa.Text),
        sa.Column("embedding", postgresql.ARRAY(sa.Float)),  # see migration 0002 — upgraded to vector(768)
        sa.Column("page_start", sa.Integer),
        sa.Column("page_end", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "spec_drawing_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("spec_section_id", sa.Integer, sa.ForeignKey("spec_sections.id"), nullable=False),
        sa.Column("symbol_id", sa.Integer, sa.ForeignKey("symbols.id")),
        sa.Column("material_run_id", sa.Integer, sa.ForeignKey("material_runs.id")),
        sa.Column("match_score", sa.Float, server_default="0.0"),
        sa.Column("match_type", sa.String(20), server_default="auto"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "takeoff_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("drawing_page_id", sa.Integer, sa.ForeignKey("drawing_pages.id")),
        sa.Column("trade_id", sa.Integer, sa.ForeignKey("trades.id")),
        sa.Column("price_book_item_id", sa.Integer, sa.ForeignKey("price_book_items.id")),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("csi_code", sa.String(20)),
        sa.Column("system", sa.String(100)),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("waste_factor", sa.Float, server_default="0.05"),
        sa.Column("adjusted_quantity", sa.Float, nullable=False),
        sa.Column("unit_material_cost", sa.Float),
        sa.Column("unit_labor_hours", sa.Float),
        sa.Column("material_total", sa.Float),
        sa.Column("labor_total", sa.Float),
        sa.Column("total_cost", sa.Float),
        sa.Column("source_symbol_ids", sa.JSON),
        sa.Column("source_run_ids", sa.JSON),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("is_locked", sa.Boolean, server_default="false"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "bids",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overhead_config_id", sa.Integer, sa.ForeignKey("overhead_configs.id")),
        sa.Column("name", sa.String(255), nullable=False, server_default="Bid v1"),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("total_material_cost", sa.Float, server_default="0"),
        sa.Column("total_labor_hours", sa.Float, server_default="0"),
        sa.Column("total_labor_cost", sa.Float, server_default="0"),
        sa.Column("total_burden", sa.Float, server_default="0"),
        sa.Column("total_overhead", sa.Float, server_default="0"),
        sa.Column("total_material_markup", sa.Float, server_default="0"),
        sa.Column("subtotal", sa.Float, server_default="0"),
        sa.Column("contingency", sa.Float, server_default="0"),
        sa.Column("bond", sa.Float, server_default="0"),
        sa.Column("permit", sa.Float, server_default="0"),
        sa.Column("profit", sa.Float, server_default="0"),
        sa.Column("grand_total", sa.Float, server_default="0"),
        sa.Column("notes", sa.Text),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "bid_line_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id", ondelete="CASCADE"), nullable=False),
        sa.Column("takeoff_item_id", sa.Integer, sa.ForeignKey("takeoff_items.id")),
        sa.Column("trade_id", sa.Integer, sa.ForeignKey("trades.id")),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("system", sa.String(100)),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("unit_material_cost", sa.Float, server_default="0"),
        sa.Column("unit_labor_hours", sa.Float, server_default="0"),
        sa.Column("labor_rate", sa.Float, server_default="0"),
        sa.Column("material_total", sa.Float, server_default="0"),
        sa.Column("labor_total", sa.Float, server_default="0"),
        sa.Column("line_total", sa.Float, server_default="0"),
        sa.Column("notes", sa.Text),
    )

    op.create_table(
        "bid_summary_sections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("group_by", sa.String(50)),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("material_subtotal", sa.Float, server_default="0"),
        sa.Column("labor_subtotal", sa.Float, server_default="0"),
        sa.Column("section_total", sa.Float, server_default="0"),
    )

    op.create_table(
        "proposals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id")),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("proposal_number", sa.String(50)),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("client_name", sa.String(255)),
        sa.Column("client_address", sa.Text),
        sa.Column("attention_to", sa.String(255)),
        sa.Column("project_description", sa.Text),
        sa.Column("scope_of_work", sa.Text),
        sa.Column("inclusions", sa.Text),
        sa.Column("exclusions", sa.Text),
        sa.Column("clarifications", sa.Text),
        sa.Column("terms_conditions", sa.Text),
        sa.Column("validity_days", sa.Integer, server_default="30"),
        sa.Column("expiry_date", sa.Date),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "equipment",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_id", sa.Integer, sa.ForeignKey("trades.id")),
        sa.Column("spec_section_id", sa.Integer, sa.ForeignKey("spec_sections.id")),
        sa.Column("submittal_id", sa.Integer),  # FK to submittals added after
        sa.Column("tag", sa.String(100)),
        sa.Column("equipment_type", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("csi_code", sa.String(20)),
        sa.Column("manufacturer", sa.String(255)),
        sa.Column("model_number", sa.String(255)),
        sa.Column("serial_number", sa.String(255)),
        sa.Column("specifications", sa.JSON),
        sa.Column("location_description", sa.String(500)),
        sa.Column("floor", sa.String(50)),
        sa.Column("room", sa.String(100)),
        sa.Column("drawing_id", sa.Integer, sa.ForeignKey("drawings.id")),
        sa.Column("drawing_coordinates", sa.JSON),
        sa.Column("is_approved", sa.Boolean, server_default="false"),
        sa.Column("is_installed", sa.Boolean, server_default="false"),
        sa.Column("notes", sa.Text),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    # Now add FK from symbols to equipment
    op.create_foreign_key(None, "symbols", "equipment", ["equipment_id"], ["id"])

    op.create_table(
        "submittals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("spec_section_id", sa.Integer, sa.ForeignKey("spec_sections.id")),
        sa.Column("equipment_id", sa.Integer, sa.ForeignKey("equipment.id")),
        sa.Column("submittal_number", sa.String(50)),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("spec_section_ref", sa.String(50)),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("revision", sa.Integer, server_default="0"),
        sa.Column("submitted_date", sa.Date),
        sa.Column("required_date", sa.Date),
        sa.Column("returned_date", sa.Date),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("reviewer_notes", sa.Text),
        sa.Column("submitter_notes", sa.Text),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_foreign_key(None, "equipment", "submittals", ["submittal_id"], ["id"])

    op.create_table(
        "submittal_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("submittal_id", sa.Integer, sa.ForeignKey("submittals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("manufacturer", sa.String(255)),
        sa.Column("model_number", sa.String(255)),
        sa.Column("quantity", sa.Integer),
        sa.Column("notes", sa.Text),
    )

    op.create_table(
        "closeout_documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("equipment_id", sa.Integer, sa.ForeignKey("equipment.id")),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("warranty_duration_months", sa.Integer),
        sa.Column("warranty_start_date", sa.Date),
        sa.Column("warranty_expiry_date", sa.Date),
        sa.Column("warranty_provider", sa.String(255)),
        sa.Column("is_received", sa.Boolean, server_default="false"),
        sa.Column("received_date", sa.Date),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("notes", sa.Text),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "feedback_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("drawing_id", sa.Integer, sa.ForeignKey("drawings.id")),
        sa.Column("before_state", sa.JSON),
        sa.Column("after_state", sa.JSON),
        sa.Column("image_crop_path", sa.String(1000)),
        sa.Column("is_training_candidate", sa.Boolean, server_default="true"),
        sa.Column("used_in_training_job_id", sa.Integer),  # FK added after ml_training_jobs
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ml_training_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("triggered_by", sa.String(50), server_default="scheduled"),
        sa.Column("triggered_by_user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("feedback_count", sa.Integer, server_default="0"),
        sa.Column("dataset_snapshot_path", sa.String(1000)),
        sa.Column("model_artifact_path", sa.String(1000)),
        sa.Column("baseline_map50", sa.Float),
        sa.Column("new_map50", sa.Float),
        sa.Column("metrics", sa.JSON),
        sa.Column("was_promoted", sa.Boolean),
        sa.Column("error_message", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_foreign_key(None, "feedback_events", "ml_training_jobs", ["used_in_training_job_id"], ["id"])


def downgrade() -> None:
    for table in [
        "ml_training_jobs", "feedback_events", "closeout_documents", "submittal_items",
        "submittals", "equipment", "proposals", "bid_summary_sections", "bid_line_items",
        "bids", "takeoff_items", "spec_drawing_links", "spec_sections", "specifications",
        "drawing_markups", "material_runs", "symbols", "drawing_pages", "drawings",
        "milestones", "tasks", "project_members", "projects", "overhead_configs",
        "labor_assemblies", "price_book_items", "trades", "users", "organizations",
    ]:
        op.drop_table(table)
