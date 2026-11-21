"""Open-Meteo-backed weather tools with defensive API handling."""

from __future__ import annotations

from typing import Any, Optional

import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10


def get_weather(city: str) -> dict[str, Any]:
    """Return validated current harvest weather for *city*, or an error payload."""
    location, error = _find_location(city)
    if error:
        return error
    data, error = _get_json(
        FORECAST_URL,
        {
            "latitude": location["latitude"], "longitude": location["longitude"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "daily": "precipitation_probability_max", "forecast_days": 1,
        },
    )
    if error:
        return error
    try:
        return {
            "city": city, "state": location.get("admin1", ""), "country": location.get("country", ""),
            "temperature": data["current"]["temperature_2m"],
            "humidity": data["current"]["relative_humidity_2m"],
            "wind_speed": data["current"]["wind_speed_10m"],
            "rain_probability": data["daily"]["precipitation_probability_max"][0],
        }
    except (KeyError, IndexError, TypeError):
        return {"error": "Weather API returned an incomplete current-weather response."}


def get_weather_forecast(city: str, days: int = 5) -> dict[str, Any]:
    """Return a validated, multi-day harvest forecast for *city*.

    ``days`` is limited to Open-Meteo's supported 1--16 day request range.
    """
    if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 16:
        return {"error": "Forecast days must be an integer between 1 and 16."}
    location, error = _find_location(city)
    if error:
        return error
    data, error = _get_json(
        FORECAST_URL,
        {
            "latitude": location["latitude"], "longitude": location["longitude"],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,relative_humidity_2m_mean,wind_speed_10m_max",
            "forecast_days": days,
        },
    )
    if error:
        return error
    try:
        daily = data["daily"]
        forecast = [
            {"date": daily["time"][index], "temperature_max": daily["temperature_2m_max"][index],
             "temperature_min": daily["temperature_2m_min"][index], "humidity": daily["relative_humidity_2m_mean"][index],
             "rain_probability": daily["precipitation_probability_max"][index], "wind_speed": daily["wind_speed_10m_max"][index]}
            for index in range(len(daily["time"]))
        ]
    except (KeyError, IndexError, TypeError):
        return {"error": "Weather API returned an incomplete forecast response."}
    return {"city": city, "forecast": forecast}


def _find_location(city: str) -> tuple[Optional[dict[str, Any]], Optional[dict[str, str]]]:
    """Resolve a city to coordinates without exposing request exceptions."""
    if not isinstance(city, str) or not city.strip():
        return None, {"error": "City must be a non-empty string."}
    data, error = _get_json(GEOCODING_URL, {"name": city, "count": 1})
    if error:
        return None, error
    try:
        location = data["results"][0]
        location["latitude"]
        location["longitude"]
        return location, None
    except (KeyError, IndexError, TypeError):
        return None, {"error": f"City '{city}' not found."}


def _get_json(url: str, params: dict[str, Any]) -> tuple[Optional[dict[str, Any]], Optional[dict[str, str]]]:
    """GET JSON with a bounded timeout and normalized external-failure payload."""
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return None, {"error": "Weather service is currently unavailable."}
    except ValueError:
        return None, {"error": "Weather service returned invalid JSON."}
    if not isinstance(data, dict):
        return None, {"error": "Weather service returned an invalid response."}
    return data, None
