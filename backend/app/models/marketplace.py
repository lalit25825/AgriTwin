import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class StakeholderProfile(Base):
    __tablename__ = "stakeholder_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    organization: Mapped[str | None] = mapped_column(String(140), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(160), nullable=True)
    village: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(240), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    commodities: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    capacity_tonnes: Mapped[float | None] = mapped_column(Float, nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    storage_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_radius_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mandi_name: Mapped[str | None] = mapped_column(String(140), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SupplyListing(Base):
    __tablename__ = "supply_listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    commodity: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    quantity_tonnes: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_tonnes: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_per_quintal: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_note: Mapped[str | None] = mapped_column(String(180), nullable=True)
    location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    pickup_location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(180), nullable=True)
    available_from: Mapped[str | None] = mapped_column(String(40), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class StakeholderConnection(Base):
    __tablename__ = "stakeholder_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    listing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("supply_listings.id", ondelete="SET NULL"), nullable=True)
    purpose: Mapped[str] = mapped_column(String(60), default="general", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    commodity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity_tonnes: Mapped[float | None] = mapped_column(Float, nullable=True)
    offered_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ConnectionMessage(Base):
    __tablename__ = "connection_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stakeholder_connections.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
