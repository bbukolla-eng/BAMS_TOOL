"""MEP platform Phase 1: regional multipliers, labor rates, assumptions/exclusions/alternates,
extended project and price-book fields, equipment cost on bid line items.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-25 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Projects: extended fields ────────────────────────────────────────────
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("client", sa.String(255), nullable=True))
        batch.add_column(sa.Column("region_code", sa.String(20), nullable=True))
        batch.add_column(sa.Column("total_sf", sa.Float, nullable=True))
        batch.add_column(sa.Column("floors", sa.Integer, nullable=True))
        batch.add_column(sa.Column("stories", sa.Integer, nullable=True))
        batch.add_column(sa.Column("complexity", sa.String(20), nullable=True, server_default="medium"))
        batch.add_column(sa.Column("is_union", sa.Boolean, nullable=False, server_default="false"))
        batch.add_column(sa.Column("target_bid_date", sa.Date, nullable=True))
    op.create_index("ix_projects_region_code", "projects", ["region_code"])

    # ── Price book items: extended fields ────────────────────────────────────
    with op.batch_alter_table("price_book_items") as batch:
        batch.add_column(sa.Column("subcategory", sa.String(100), nullable=True))
        batch.add_column(sa.Column("equipment_unit_cost", sa.Float, nullable=False, server_default="0"))
        batch.add_column(sa.Column("material_markup_pct", sa.Float, nullable=True))
        batch.add_column(sa.Column("labor_markup_pct", sa.Float, nullable=True))
        batch.add_column(sa.Column("region_code", sa.String(20), nullable=True))
        batch.add_column(sa.Column("source", sa.String(100), nullable=True))
    op.create_index("ix_price_book_items_subcategory", "price_book_items", ["subcategory"])
    op.create_index("ix_price_book_items_region_code", "price_book_items", ["region_code"])

    # ── Bids: regional multiplier snapshot + equipment total ─────────────────
    with op.batch_alter_table("bids") as batch:
        batch.add_column(sa.Column("regional_multiplier", sa.Float, nullable=False, server_default="1"))
        batch.add_column(sa.Column("region_code", sa.String(40), nullable=True))
        batch.add_column(sa.Column("total_equipment_cost", sa.Float, nullable=False, server_default="0"))

    # ── BidLineItem: equipment ──────────────────────────────────────────────
    with op.batch_alter_table("bid_line_items") as batch:
        batch.add_column(sa.Column("unit_equipment_cost", sa.Float, nullable=False, server_default="0"))
        batch.add_column(sa.Column("equipment_total", sa.Float, nullable=False, server_default="0"))

    # ── Regional multipliers ────────────────────────────────────────────────
    op.create_table(
        "regional_multipliers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("is_metro", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("material_multiplier", sa.Float, nullable=False, server_default="1"),
        sa.Column("labor_multiplier", sa.Float, nullable=False, server_default="1"),
        sa.Column("equipment_multiplier", sa.Float, nullable=False, server_default="1"),
        sa.Column("total_multiplier", sa.Float, nullable=False, server_default="1"),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_regional_multipliers_code", "regional_multipliers", ["code"])
    op.create_index("ix_regional_multipliers_state", "regional_multipliers", ["state"])

    # ── Labor rates (region × category) ─────────────────────────────────────
    op.create_table(
        "labor_rates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("region_code", sa.String(40), nullable=False),
        sa.Column("trade_category", sa.String(40), nullable=False),
        sa.Column("hourly_rate", sa.Float, nullable=False),
        sa.Column("foreman_rate", sa.Float, nullable=True),
        sa.Column("is_union", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_labor_rates_region_code", "labor_rates", ["region_code"])
    op.create_index("ix_labor_rates_trade_category", "labor_rates", ["trade_category"])

    # ── Bid assumptions / exclusions / alternates ───────────────────────────
    for table in ("bid_assumptions", "bid_exclusions"):
        op.create_table(
            table,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("text", sa.Text, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(f"ix_{table}_bid_id", table, ["bid_id"])

    op.create_table(
        "bid_alternates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bid_id", sa.Integer, sa.ForeignKey("bids.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("is_add", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("cost_impact", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bid_alternates_bid_id", "bid_alternates", ["bid_id"])


def downgrade() -> None:
    op.drop_table("bid_alternates")
    op.drop_table("bid_exclusions")
    op.drop_table("bid_assumptions")
    op.drop_table("labor_rates")
    op.drop_table("regional_multipliers")

    with op.batch_alter_table("bid_line_items") as batch:
        batch.drop_column("equipment_total")
        batch.drop_column("unit_equipment_cost")

    with op.batch_alter_table("bids") as batch:
        batch.drop_column("total_equipment_cost")
        batch.drop_column("region_code")
        batch.drop_column("regional_multiplier")

    op.drop_index("ix_price_book_items_region_code", table_name="price_book_items")
    op.drop_index("ix_price_book_items_subcategory", table_name="price_book_items")
    with op.batch_alter_table("price_book_items") as batch:
        batch.drop_column("source")
        batch.drop_column("region_code")
        batch.drop_column("labor_markup_pct")
        batch.drop_column("material_markup_pct")
        batch.drop_column("equipment_unit_cost")
        batch.drop_column("subcategory")

    op.drop_index("ix_projects_region_code", table_name="projects")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("target_bid_date")
        batch.drop_column("is_union")
        batch.drop_column("complexity")
        batch.drop_column("stories")
        batch.drop_column("floors")
        batch.drop_column("total_sf")
        batch.drop_column("region_code")
        batch.drop_column("client")
