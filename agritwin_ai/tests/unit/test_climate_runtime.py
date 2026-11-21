from types import SimpleNamespace
from unittest.mock import Mock

from agritwin_ai.agents.climate.evaluator import ClimateEvaluator
from agritwin_ai.agents.climate.tool_schema import TOOLS
from agritwin_ai.agents.climate.workflow import ClimateWorkflow
from agritwin_ai.runtime.engine import AgentEngine


def test_climate_agent_uses_generic_runtime_for_deterministic_decision() -> None:
    engine = AgentEngine(
        prompt="system",
        workflow_factory=ClimateWorkflow,
        evaluator=ClimateEvaluator(),
        tools=TOOLS,
        decision_label="climate",
    )
    engine.memory_manager.update_working({"city": "Nashik"})
    engine.pipeline.prepare = Mock(return_value=(SimpleNamespace(intent="climate_summary"), []))
    engine.reasoning.think = Mock(side_effect=[
        ("weather", {"type": "tool", "data": {"action": "get_weather", "arguments": {"city": "Nashik"}}}),
        ("final", {"type": "final", "data": "Conditions are stable."}),
    ])
    engine.tool_executor.execute = Mock(return_value=(True, {
        "temperature": 25, "humidity": 50, "rain_probability": 5, "wind_speed": 8,
    }))

    response = engine.run("What is the weather?")

    assert response.startswith("Deterministic climate decision: LOW")
    assert engine.workflow.state.completed is True
