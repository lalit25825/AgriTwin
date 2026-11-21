from unittest.mock import Mock, patch

from agritwin_ai.tools.weather.weather import get_weather, get_weather_forecast


def _response(payload: dict) -> Mock:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


@patch("agritwin_ai.tools.weather.weather.requests.get")
def test_get_weather_returns_normalized_current_conditions(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _response({"results": [{"latitude": 19.9, "longitude": 73.8, "country": "India", "admin1": "Maharashtra"}]}),
        _response({"current": {"temperature_2m": 25, "relative_humidity_2m": 55, "wind_speed_10m": 8},
                   "daily": {"precipitation_probability_max": [20]}}),
    ]
    result = get_weather("Nashik")
    assert result["temperature"] == 25
    assert result["rain_probability"] == 20


@patch("agritwin_ai.tools.weather.weather.requests.get")
def test_get_weather_forecast_includes_wind(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _response({"results": [{"latitude": 19.9, "longitude": 73.8}]}),
        _response({"daily": {"time": ["2026-08-03"], "temperature_2m_max": [28],
                   "temperature_2m_min": [18], "precipitation_probability_max": [10],
                   "relative_humidity_2m_mean": [50], "wind_speed_10m_max": [12]}}),
    ]
    result = get_weather_forecast("Nashik", 1)
    assert result["forecast"][0]["wind_speed"] == 12


def test_get_weather_forecast_rejects_invalid_day_count() -> None:
    assert "error" in get_weather_forecast("Nashik", 0)
