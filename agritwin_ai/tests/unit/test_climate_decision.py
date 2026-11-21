from agritwin_ai.decision.climate import evaluate_climate


def test_climate_decision_reports_safe_conditions() -> None:
    decision = evaluate_climate(
        weather={"temperature": 25, "humidity": 50, "rain_probability": 10, "wind_speed": 8}
    )

    assert decision["overall_risk"] == "LOW"
    assert decision["field_access"] is True


def test_climate_decision_blocks_heavy_rain() -> None:
    decision = evaluate_climate(
        weather={"temperature": 25, "humidity": 90, "rain_probability": 90, "wind_speed": 35}
    )

    assert decision["overall_risk"] == "HIGH"
    assert decision["field_access"] is False
