import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class FarmPlot(Base):
    __tablename__ = "farm_plots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    crop: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    variety: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sowing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    area_acres: Mapped[float | None] = mapped_column(Float, nullable=True)
    crop_stage: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    irrigation_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    soil_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class StakeholderOperation(Base):
    __tablename__ = "stakeholder_operations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    operation_type: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="planned", index=True, nullable=False)
    commodity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity_tonnes: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin: Mapped[str | None] = mapped_column(String(180), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(180), nullable=True)
    scheduled_at: Mapped[str | None] = mapped_column(String(48), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
