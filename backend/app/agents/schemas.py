from typing import Literal
from pydantic import BaseModel, Field


CropStage = Literal[
    "unknown", "sowing", "vegetative", "flowering", "grain_filling",
    "maturity", "ready", "harvested"
]


class AgentRunRequest(BaseModel):
    query: str | None = Field(default=None, max_length=2000)
    crop: str = Field(default="Soybean", min_length=2, max_length=80)
    crop_stage: CropStage = "unknown"
    location: str | None = Field(default=None, max_length=160)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    quantity_tonnes: float | None = Field(default=None, gt=0, le=100000)
    origin: str | None = Field(default=None, max_length=240)
    destination: str | None = Field(default=None, max_length=240)
    commodity: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    mandi: str | None = Field(default=None, max_length=100)
    expected_sale_price: float | None = Field(default=None, gt=0)
    production_cost_per_quintal: float | None = Field(default=None, gt=0)


class AgentStatus(BaseModel):
    id: str
    name: str
    description: str
    status: str
    capability: str
