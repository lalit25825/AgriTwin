from dataclasses import dataclass


@dataclass
class ClimateState:

    city: str | None = None

    district: str | None = None

    state: str | None = None

    country: str | None = None

    current_weather: dict | None = None

    forecast: dict | None = None

    alerts: dict | None = None

    climate_summary: dict | None = None

    decision: dict | None = None

    completed: bool = False

    quantity: int | None = None