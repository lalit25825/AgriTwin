from agritwin_ai.agents.climate.workflow import ClimateWorkflow


def test_climate_workflow_reuses_city_from_working_memory() -> None:
    class Item:
        value = "Nashik"

    workflow = ClimateWorkflow()
    workflow.load_memory({"city": Item()})

    assert workflow.reflect("weather_forecast") == {"ready": True, "missing": []}


def test_climate_workflow_rejects_error_observation() -> None:
    workflow = ClimateWorkflow()
    workflow.set_current_weather({"error": "unavailable"})

    assert workflow.ready_for_evaluation() is False
