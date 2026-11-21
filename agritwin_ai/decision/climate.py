"""Deterministic climate-risk evaluation with no LLM dependency."""

from __future__ import annotations

from typing import Any, Mapping

from agritwin_ai.agents.climate.knowledge import CLIMATE_THRESHOLDS


def evaluate_climate(
    weather: Mapping[str, Any] | None = None,
    forecast: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute field-operation climate risks from current weather or a forecast.

    Forecast evaluation intentionally uses the most adverse value for each factor,
    producing a conservative deterministic recommendation for field operations.
    """
    values = _weather_values(weather, forecast)
    if values is None:
        return {"error": "Climate evaluation requires complete weather or forecast data."}

    rain_risk = "HIGH" if values["rain"] >= CLIMATE_THRESHOLDS["heavy_rain"] else "LOW"
    wind_risk = "HIGH" if values["wind"] >= CLIMATE_THRESHOLDS["strong_wind"] else "LOW"
    humidity_risk = "HIGH" if values["humidity"] >= CLIMATE_THRESHOLDS["high_humidity"] else "LOW"
    temperature_risk = (
        "HIGH"
        if values["temperature"] >= CLIMATE_THRESHOLDS["heatwave"]
        or values["temperature"] <= CLIMATE_THRESHOLDS["coldwave"]
        else "LOW"
    )
    risks = {
        "rain_risk": rain_risk,
        "wind_risk": wind_risk,
        "temperature_risk": temperature_risk,
        "humidity_risk": humidity_risk,
    }
    high_risks = sum(level == "HIGH" for level in risks.values())
    field_access = rain_risk == "LOW"
    overall_risk = "HIGH" if high_risks else "LOW"
    confidence = round(max(0.0, 1.0 - high_risks * 0.1), 2)

    alerts = []
    if rain_risk == "HIGH":
        alerts.append("Heavy rainfall expected.")
    if wind_risk == "HIGH":
        alerts.append("Strong winds expected.")
    if humidity_risk == "HIGH":
        alerts.append("Humidity is very high.")
    if values["temperature"] >= CLIMATE_THRESHOLDS["heatwave"]:
        alerts.append("Heatwave conditions.")
    if values["temperature"] <= CLIMATE_THRESHOLDS["coldwave"]:
        alerts.append("Coldwave conditions.")

    return {
        "decision": overall_risk,
        "overall_risk": overall_risk,
        **risks,
        "field_access": field_access,
        "recommended_action": (
            "Avoid field operations until weather improves."
            if overall_risk == "HIGH"
            else "Weather conditions are suitable for field operations."
        ),
        "confidence": confidence,
        "alerts": alerts,
    }


def _weather_values(
    weather: Mapping[str, Any] | None,
    forecast: Mapping[str, Any] | None,
) -> dict[str, float] | None:
    """Normalize current weather or the adverse values from forecast days."""
    try:
        if weather is not None:
            return {
                "temperature": float(weather["temperature"]),
                "humidity": float(weather["humidity"]),
                "rain": float(weather["rain_probability"]),
                "wind": float(weather["wind_speed"]),
            }
        days = forecast["forecast"] if forecast is not None else []
        if not days:
            return None
        return {
            "temperature": max(float(day["temperature_max"]) for day in days),
            "humidity": max(float(day["humidity"]) for day in days),
            "rain": max(float(day["rain_probability"]) for day in days),
            "wind": max(float(day["wind_speed"]) for day in days),
        }
    except (KeyError, TypeError, ValueError):
        return None
