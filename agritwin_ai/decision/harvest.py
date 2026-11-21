"""
Harvest Decision Engine

This module contains deterministic agricultural rules for
evaluating whether harvesting is safe.

It does NOT call the LLM.

Its job is to transform weather + crop knowledge into an
explainable recommendation.
"""

from typing import Any


def evaluate_harvest(weather: dict[str, Any], crop: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate whether harvesting should proceed.

    Args:
        weather:
            Weather information from the Weather Tool.

        crop:
            Crop knowledge from the Knowledge Base.

    Returns:
        Structured harvest recommendation.
    """

    reasons = []
    confidence = 1.0
    risk_score = 0

    temperature = weather["temperature"]
    humidity = weather["humidity"]
    rain_probability = weather["rain_probability"]
    wind_speed = weather["wind_speed"]

    # -------------------------
    # Rain Check
    # -------------------------

    if crop["rain_sensitive"] and rain_probability > 50:
        risk_score += 3
        confidence -= 0.20

        reasons.append(
            f"Rain probability is {rain_probability}%, which is unsafe for harvesting."
        )

    # -------------------------
    # Humidity Check
    # -------------------------

    if humidity > crop["max_humidity"]:
        risk_score += 2
        confidence -= 0.15

        reasons.append(
            f"Humidity is {humidity}%, exceeding the safe limit of {crop['max_humidity']}%."
        )

    # -------------------------
    # Temperature Check
    # -------------------------

    if temperature < crop["ideal_temperature"]["min"]:
        risk_score += 1
        confidence -= 0.10

        reasons.append(
            f"Temperature ({temperature}°C) is below the ideal harvesting range."
        )

    elif temperature > crop["ideal_temperature"]["max"]:
        risk_score += 1
        confidence -= 0.10

        reasons.append(
            f"Temperature ({temperature}°C) is above the ideal harvesting range."
        )

    # -------------------------
    # Wind Check
    # -------------------------

    wind_limit = crop.get("ideal_wind_speed", 30)
    if wind_speed > wind_limit:
        risk_score += 1
        confidence -= 0.05

        reasons.append(
            f"Wind speed ({wind_speed} km/h) exceeds the safe limit of {wind_limit} km/h."
        )

    confidence = max(round(confidence, 2), 0.0)

    # -------------------------
    # Safe
    # -------------------------

    if risk_score == 0:

        return {
            "decision": "HARVEST",
            "confidence": confidence,
            "risk_level": "LOW",
            "reasons": [
                "Weather conditions are within the recommended harvesting limits."
            ],
            "recommended_action": "Harvest can proceed safely."
        }

    # -------------------------
    # Risk Level
    # -------------------------

    if risk_score >= 5:
        risk = "HIGH"
    elif risk_score >= 3:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "decision": "DELAY",
        "confidence": confidence,
        "risk_level": risk,
        "reasons": reasons,
        "recommended_action":
            "Delay harvesting and review the weather forecast again in the next 24 hours."
    }
