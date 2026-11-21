"""Deterministic forecast-based harvest decisions."""

from __future__ import annotations

from typing import Any, Iterable


def find_best_harvest_day(forecast: Iterable[dict[str, Any]], crop: dict[str, Any]) -> dict[str, Any]:
    """Score every forecast day and return the safest valid harvest window.

    Rain, humidity, average temperature, and wind are all deterministic inputs.
    A day must satisfy all crop thresholds to be a harvest candidate.
    """
    candidates: list[tuple[float, dict[str, Any]]] = []
    for day in forecast:
        score, reasons = _score_day(day, crop)
        if not reasons:
            candidates.append((score, day))

    if not candidates:
        return {
            "decision": "DELAY",
            "best_day": None,
            "confidence": 0.95,
            "reason": "No forecast day satisfies the crop's rain, humidity, temperature, and wind limits.",
        }

    score, best = max(candidates, key=lambda candidate: (candidate[0], candidate[1]["date"]))
    temperature_average = (best["temperature_min"] + best["temperature_max"]) / 2
    ideal_temperature = crop["ideal_temperature"]
    return {
        "decision": "HARVEST",
        "best_day": best["date"],
        "confidence": round(min(0.99, 0.75 + score / 400), 2),
        "reason": "Selected the highest-scoring day whose daily average temperature and other evaluated weather measures meet the configured crop limits.",
        "weather_summary": {
            "temperature_min_c": best["temperature_min"],
            "temperature_max_c": best["temperature_max"],
            "temperature_average_c": round(temperature_average, 2),
            "ideal_temperature_range_c": [ideal_temperature["min"], ideal_temperature["max"]],
            "average_temperature_within_ideal_range": (
                ideal_temperature["min"] <= temperature_average <= ideal_temperature["max"]
            ),
            "rain_probability_pct": best["rain_probability"],
            "humidity_pct": best["humidity"],
            "wind_speed_kmh": best.get("wind_speed"),
        },
        "temperature_evaluation": (
            "The configured rule evaluates the average of the daily minimum and maximum. "
            "The reported minimum and maximum may individually fall outside the ideal range."
        ),
        "scope_note": (
            "This is a weather-window recommendation only. Confirm onion maturity and "
            "field conditions before harvesting; weather suitability alone does not prove crop readiness."
        ),
    }


def _score_day(day: dict[str, Any], crop: dict[str, Any]) -> tuple[float, list[str]]:
    """Return a transparent score and disqualifying-threshold failures for one day."""
    temperature = (day["temperature_min"] + day["temperature_max"]) / 2
    ideal_temperature = crop["ideal_temperature"]
    rain_limit = 50 if crop["rain_sensitive"] else 75
    wind_limit = crop.get("ideal_wind_speed", 30)
    wind = day.get("wind_speed", 0)
    reasons: list[str] = []

    if day["rain_probability"] > rain_limit:
        reasons.append("rain probability exceeds the crop limit")
    if day["humidity"] > crop["max_humidity"]:
        reasons.append("humidity exceeds the crop limit")
    if not ideal_temperature["min"] <= temperature <= ideal_temperature["max"]:
        reasons.append("temperature is outside the crop range")
    if wind > wind_limit:
        reasons.append("wind speed exceeds the crop limit")

    midpoint = (ideal_temperature["min"] + ideal_temperature["max"]) / 2
    temperature_score = max(0.0, 30 - abs(temperature - midpoint) * 3)
    humidity_score = max(0.0, 25 - day["humidity"] / max(crop["max_humidity"], 1) * 25)
    rain_score = max(0.0, 25 - day["rain_probability"] / max(rain_limit, 1) * 25)
    wind_score = max(0.0, 20 - wind / max(wind_limit, 1) * 20)
    return temperature_score + humidity_score + rain_score + wind_score, reasons
