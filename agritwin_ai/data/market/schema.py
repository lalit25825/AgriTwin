from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MarketRecord(BaseModel):
    """
    Canonical provider-neutral representation of an agricultural
    market observation.
    """

    model_config = ConfigDict(extra="forbid")

    date: date

    state: str
    district: str | None = None
    market: str
    commodity: str

    variety: str | None = None
    grade: str | None = None

    arrival_quantity: float | None = Field(
        default=None,
        ge=0,
    )

    min_price: float = Field(ge=0)
    max_price: float = Field(ge=0)
    modal_price: float = Field(ge=0)

    source: str

    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator(
        "state",
        "market",
        "commodity",
        "source",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Required text field cannot be empty."
            )

        return value

    @field_validator(
        "district",
        "variety",
        "grade",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @model_validator(mode="after")
    def validate_price_relationships(self) -> "MarketRecord":
        if self.max_price < self.min_price:
            raise ValueError(
                "max_price cannot be less than min_price."
            )

        if not self.min_price <= self.modal_price <= self.max_price:
            raise ValueError(
                "modal_price must be between min_price and max_price."
            )

        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()