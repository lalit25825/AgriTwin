"""Add stakeholder profiles, listings, connections and messages.

Revision ID: 7c4b2a91e6f0
Revises: 1d0311fc0ceb
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "7c4b2a91e6f0"
down_revision: Union[str, Sequence[str], None] = "1d0311fc0ceb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve legacy role values and add the explicit stakeholder roles used by the new UI.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'driver'")
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'storage_owner'")
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'mandi_seller'")
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'mandi_owner'")
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'fpo_manager'")

    op.create_table(
        "stakeholder_profiles",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization", sa.String(140), nullable=True),
        sa.Column("headline", sa.String(160), nullable=True),
        sa.Column("village", sa.String(100), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("address", sa.String(240), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("about", sa.Text(), nullable=True),
        sa.Column("commodities", sa.JSON(), nullable=True),
        sa.Column("capacity_tonnes", sa.Float(), nullable=True),
        sa.Column("vehicle_type", sa.String(100), nullable=True),
        sa.Column("storage_type", sa.String(100), nullable=True),
        sa.Column("service_radius_km", sa.Integer(), nullable=True),
        sa.Column("mandi_name", sa.String(140), nullable=True),
        sa.Column("license_number", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_stakeholder_profiles_district", "stakeholder_profiles", ["district"])
    op.create_index("ix_stakeholder_profiles_state", "stakeholder_profiles", ["state"])

    op.create_table(
        "supply_listings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("commodity", sa.String(100), nullable=True),
        sa.Column("quantity_tonnes", sa.Float(), nullable=True),
        sa.Column("capacity_tonnes", sa.Float(), nullable=True),
        sa.Column("price_per_quintal", sa.Float(), nullable=True),
        sa.Column("price_note", sa.String(180), nullable=True),
        sa.Column("location", sa.String(180), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("pickup_location", sa.String(180), nullable=True),
        sa.Column("destination", sa.String(180), nullable=True),
        sa.Column("available_from", sa.String(40), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("owner_id", "category", "commodity", "district", "state", "is_active"):
        op.create_index(f"ix_supply_listings_{col}", "supply_listings", [col])

    op.create_table(
        "stakeholder_connections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("requester_id", sa.UUID(), nullable=False),
        sa.Column("recipient_id", sa.UUID(), nullable=False),
        sa.Column("listing_id", sa.UUID(), nullable=True),
        sa.Column("purpose", sa.String(60), nullable=False, server_default="general"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("commodity", sa.String(100), nullable=True),
        sa.Column("quantity_tonnes", sa.Float(), nullable=True),
        sa.Column("offered_price", sa.Float(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["supply_listings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stakeholder_connections_requester_id", "stakeholder_connections", ["requester_id"])
    op.create_index("ix_stakeholder_connections_recipient_id", "stakeholder_connections", ["recipient_id"])
    op.create_index("ix_stakeholder_connections_status", "stakeholder_connections", ["status"])

    op.create_table(
        "connection_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("connection_id", sa.UUID(), nullable=False),
        sa.Column("sender_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["stakeholder_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_connection_messages_connection_id", "connection_messages", ["connection_id"])
    op.create_index("ix_connection_messages_sender_id", "connection_messages", ["sender_id"])


def downgrade() -> None:
    op.drop_index("ix_connection_messages_sender_id", table_name="connection_messages")
    op.drop_index("ix_connection_messages_connection_id", table_name="connection_messages")
    op.drop_table("connection_messages")
    op.drop_index("ix_stakeholder_connections_status", table_name="stakeholder_connections")
    op.drop_index("ix_stakeholder_connections_recipient_id", table_name="stakeholder_connections")
    op.drop_index("ix_stakeholder_connections_requester_id", table_name="stakeholder_connections")
    op.drop_table("stakeholder_connections")
    for col in ("is_active", "state", "district", "commodity", "category", "owner_id"):
        op.drop_index(f"ix_supply_listings_{col}", table_name="supply_listings")
    op.drop_table("supply_listings")
    op.drop_index("ix_stakeholder_profiles_state", table_name="stakeholder_profiles")
    op.drop_index("ix_stakeholder_profiles_district", table_name="stakeholder_profiles")
    op.drop_table("stakeholder_profiles")
