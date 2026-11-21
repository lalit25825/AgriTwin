from agritwin_ai.decision.forecast import find_best_harvest_day
from agritwin_ai.decision.harvest import evaluate_harvest


def _crop() -> dict:
    return {"rain_sensitive": True, "max_humidity": 70,
            "ideal_temperature": {"min": 15, "max": 30}, "ideal_wind_speed": 20}


def test_evaluate_harvest_returns_harvest_for_safe_weather() -> None:
    decision = evaluate_harvest(
        {"temperature": 24, "humidity": 60, "rain_probability": 10, "wind_speed": 10}, _crop())
    assert decision["decision"] == "HARVEST"


def test_evaluate_harvest_returns_delay_for_high_risk_weather() -> None:
    decision = evaluate_harvest(
        {"temperature": 10, "humidity": 90, "rain_probability": 80, "wind_speed": 35}, _crop())
    assert decision["decision"] == "DELAY"
    assert decision["risk_level"] == "HIGH"


def test_forecast_selects_highest_scoring_valid_day_not_first_valid_day() -> None:
    decision = find_best_harvest_day([
        {"date": "2026-08-03", "temperature_min": 15, "temperature_max": 25,
         "humidity": 65, "rain_probability": 40, "wind_speed": 18},
        {"date": "2026-08-04", "temperature_min": 20, "temperature_max": 26,
         "humidity": 45, "rain_probability": 5, "wind_speed": 5},
    ], _crop())
    assert decision["decision"] == "HARVEST"
    assert decision["best_day"] == "2026-08-04"


def test_forecast_delays_when_no_day_meets_thresholds() -> None:
    decision = find_best_harvest_day([
        {"date": "2026-08-03", "temperature_min": 15, "temperature_max": 25,
         "humidity": 90, "rain_probability": 80, "wind_speed": 25},
    ], _crop())
    assert decision["decision"] == "DELAY"
    assert decision["best_day"] is None
