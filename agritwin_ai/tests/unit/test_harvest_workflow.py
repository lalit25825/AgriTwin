from agritwin_ai.agents.harvest.workflow import HarvestWorkflow


def test_reflection_requires_crop_and_city_for_harvest() -> None:
    reflection = HarvestWorkflow().reflect("harvest_decision")
    assert reflection == {"ready": False, "missing": ["crop", "city"]}


def test_workflow_loads_crop_and_city_from_working_memory() -> None:
    class Item:
        def __init__(self, value: str) -> None:
            self.value = value

    workflow = HarvestWorkflow()
    workflow.load_memory({"crop": Item("onion"), "city": Item("Nashik")})
    assert workflow.reflect("harvest_forecast")["ready"] is True
