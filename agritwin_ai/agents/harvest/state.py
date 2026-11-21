from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class HarvestState:

    # User Information
    crop: Optional[str] = None

    city: Optional[str] = None

    # Date for specific date queries (e.g., "25 August")
    date: Optional[str] = None

    # Current Weather
    weather: Optional[dict[str, Any]] = None

    # Multi-day Forecast
    forecast: Optional[dict[str, Any]] = None

    # Crop Knowledge
    crop_info: Optional[dict[str, Any]] = None

    # Final Decision
    decision: Optional[dict[str, Any]] = None

    # Workflow Status
    completed = False
