from types import SimpleNamespace
from unittest.mock import Mock

from agritwin_ai.runtime.engine import AgentEngine
from agritwin_ai.agents.harvest.evaluator import HarvestEvaluator
from agritwin_ai.agents.harvest.tool_schema import TOOLS
from agritwin_ai.agents.harvest.workflow import HarvestWorkflow


def _engine() -> AgentEngine:
    return AgentEngine(
        prompt="system",
        workflow_factory=HarvestWorkflow,
        evaluator=HarvestEvaluator(),
        tools=TOOLS,
        decision_label="harvest",
    )


def test_engine_runs_deterministic_decision_before_final_explanation() -> None:
    engine = _engine()
    engine.memory_manager.update_working({"crop": "onion", "city": "Nashik"})
    engine.pipeline.prepare = Mock(return_value=(SimpleNamespace(intent="harvest_decision"), []))
    engine.reasoning.think = Mock(side_effect=[
        ("crop", {"type": "tool", "data": {"action": "get_crop_info", "arguments": {"crop": "onion"}}}),
        ("weather", {"type": "tool", "data": {"action": "get_weather", "arguments": {"city": "Nashik"}}}),
        ("final", {"type": "final", "data": "Conditions are suitable."}),
    ])
    engine.tool_executor.execute = Mock(side_effect=[
        (True, {"rain_sensitive": True, "max_humidity": 70,
                "ideal_temperature": {"min": 15, "max": 30}, "ideal_wind_speed": 20}),
        (True, {"temperature": 24, "humidity": 50, "rain_probability": 5, "wind_speed": 8}),
    ])

    response = engine.run("Should I harvest today?")

    assert response.startswith("Deterministic harvest decision: HARVEST")
    assert engine.workflow.state.completed is True


def test_engine_replaces_workflow_for_each_request() -> None:
    engine = _engine()
    old_workflow = engine.workflow
    engine.pipeline.prepare = Mock(return_value=(SimpleNamespace(intent="greeting"), []))
    engine.reasoning.think = Mock(return_value=("final", {"type": "final", "data": "Hello"}))

    assert engine.run("Hello") == "Hello"
    assert engine.workflow is not old_workflow
