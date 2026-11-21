"""Add farm plots and role-specific operational records.

Revision ID: 9a6d4c2e1f70
Revises: 7c4b2a91e6f0
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "9a6d4c2e1f70"
down_revision: Union[str, Sequence[str], None] = "7c4b2a91e6f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "farm_plots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("farmer_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("crop", sa.String(80), nullable=False),
        sa.Column("variety", sa.String(100), nullable=True),
        sa.Column("sowing_date", sa.Date(), nullable=True),
        sa.Column("area_acres", sa.Float(), nullable=True),
        sa.Column("crop_stage", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("irrigation_type", sa.String(80), nullable=True),
        sa.Column("soil_type", sa.String(80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["farmer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farm_plots_farmer_id", "farm_plots", ["farmer_id"])
    op.create_index("ix_farm_plots_crop", "farm_plots", ["crop"])

    op.create_table(
        "stakeholder_operations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("operation_type", sa.String(48), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="planned"),
        sa.Column("commodity", sa.String(100), nullable=True),
        sa.Column("quantity_tonnes", sa.Float(), nullable=True),
        sa.Column("origin", sa.String(180), nullable=True),
        sa.Column("destination", sa.String(180), nullable=True),
        sa.Column("scheduled_at", sa.String(48), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stakeholder_operations_owner_id", "stakeholder_operations", ["owner_id"])
    op.create_index("ix_stakeholder_operations_operation_type", "stakeholder_operations", ["operation_type"])
    op.create_index("ix_stakeholder_operations_status", "stakeholder_operations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_stakeholder_operations_status", table_name="stakeholder_operations")
    op.drop_index("ix_stakeholder_operations_operation_type", table_name="stakeholder_operations")
    op.drop_index("ix_stakeholder_operations_owner_id", table_name="stakeholder_operations")
    op.drop_table("stakeholder_operations")
    op.drop_index("ix_farm_plots_crop", table_name="farm_plots")
    op.drop_index("ix_farm_plots_farmer_id", table_name="farm_plots")
    op.drop_table("farm_plots")
