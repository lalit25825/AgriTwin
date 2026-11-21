import httpx
from backend.app.agents.schemas import AgentRunRequest


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def run(request: AgentRunRequest) -> dict:
    if request.latitude is None or request.longitude is None:
        return {
            "id": "climate", "name": "Climate Agent", "status": "needs_input",
            "headline": "Farm coordinates required",
            "summary": "Add the farm latitude and longitude to retrieve a location-specific live forecast.",
            "data": {}, "actions": ["Enter farm coordinates in the analysis form"],
            "source": "Open-Meteo forecast API", "live": False,
        }

    params = {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max",
        "forecast_days": 3,
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            payload = response.json()
        current = payload.get("current", {})
        daily = payload.get("daily", {})
        dates = daily.get("time", [])
        forecast = []
        for index, day in enumerate(dates):
            forecast.append({
                "date": day,
                "max_temp_c": _at(daily, "temperature_2m_max", index),
                "min_temp_c": _at(daily, "temperature_2m_min", index),
                "rain_probability_pct": _at(daily, "precipitation_probability_max", index),
                "rain_mm": _at(daily, "precipitation_sum", index),
                "max_wind_kmh": _at(daily, "wind_speed_10m_max", index),
            })
        rain_today = _at(daily, "precipitation_sum", 0)
        alerts = []
        if isinstance(rain_today, (int, float)) and rain_today >= 10:
            alerts.append("Rain is forecast: review spraying, drying, and harvest plans.")
        wind_today = _at(daily, "wind_speed_10m_max", 0)
        if isinstance(wind_today, (int, float)) and wind_today >= 30:
            alerts.append("Elevated wind is forecast: review spray drift and field-work safety.")
        if not alerts:
            alerts.append("No threshold-based weather flag from the returned three-day forecast.")
        return {
            "id": "climate", "name": "Climate Agent", "status": "completed",
            "headline": "Live local forecast retrieved",
            "summary": "Current conditions and a three-day forecast are available for the supplied coordinates.",
            "data": {
                "current": {
                    "temperature_c": current.get("temperature_2m"),
                    "humidity_pct": current.get("relative_humidity_2m"),
                    "precipitation_mm": current.get("precipitation"),
                    "weather_code": current.get("weather_code"),
                    "wind_kmh": current.get("wind_speed_10m"),
                    "time": current.get("time"),
                },
                "forecast": forecast,
                "alerts": alerts,
                "timezone": payload.get("timezone"),
            },
            "actions": alerts,
            "source": "Open-Meteo API", "live": True,
        }
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        return {
            "id": "climate", "name": "Climate Agent", "status": "unavailable",
            "headline": "Forecast provider unavailable",
            "summary": "The weather request could not be completed. Check connectivity and retry; no weather values were fabricated.",
            "data": {"reason": str(exc)[:240]}, "actions": ["Retry the climate analysis"],
            "source": "Open-Meteo API", "live": False,
        }


def _at(mapping: dict, key: str, index: int):
    values = mapping.get(key) or []
    return values[index] if index < len(values) else None
