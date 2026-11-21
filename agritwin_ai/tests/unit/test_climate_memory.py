from agritwin_ai.agents.climate.workflow import ClimateWorkflow
from agritwin_ai.memory.manager import MemoryManager


def test_climate_workflow_reuses_persisted_working_city() -> None:
    memory = MemoryManager()
    memory.update_working({"city": "Nashik"})
    workflow = ClimateWorkflow()

    workflow.load_memory(memory.get_working())

    assert workflow.reflect("rainfall_forecast")["ready"] is True
