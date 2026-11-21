from agritwin_ai.agents.harvest.workflow import HarvestWorkflow
from agritwin_ai.agents.harvest.evaluator import HarvestEvaluator
from agritwin_ai.runtime.decision_manager import DecisionManager


def _crop() -> dict:
    return {
        "rain_sensitive": True,
        "max_humidity": 70,
        "ideal_temperature": {"min": 15, "max": 30},
        "ideal_wind_speed": 20,
    }


def test_decision_manager_uses_current_weather_for_current_intent() -> None:
    workflow = HarvestWorkflow()
    workflow.set_crop_info(_crop())
    workflow.set_weather(
        {"temperature": 24, "humidity": 55, "wind_speed": 10, "rain_probability": 10}
    )

    context = DecisionManager().run(workflow, "harvest_decision", HarvestEvaluator())

    assert workflow.state.decision["decision"] == "HARVEST"
    assert context is not None
    assert "IMMUTABLE DETERMINISTIC DECISION" in context["content"]


def test_decision_manager_uses_forecast_for_forecast_intent() -> None:
    workflow = HarvestWorkflow()
    workflow.set_crop_info(_crop())
    workflow.set_forecast(
        {"forecast": [{"date": "2026-08-03", "temperature_min": 20,
                       "temperature_max": 26, "humidity": 50,
                       "rain_probability": 0, "wind_speed": 8}]}
    )

    DecisionManager().run(workflow, "harvest_forecast", HarvestEvaluator())

    assert workflow.state.decision["best_day"] == "2026-08-03"


def test_decision_manager_rejects_tool_error_payload() -> None:
    workflow = HarvestWorkflow()
    workflow.set_crop_info(_crop())
    workflow.set_weather({"error": "Weather API unavailable"})

    assert DecisionManager().run(workflow, "harvest_decision", HarvestEvaluator()) is None
    assert workflow.state.decision is None
