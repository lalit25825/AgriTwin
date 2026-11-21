from agritwin_ai.agents.coordinator.agent import create_engine
from agritwin_ai.agents.coordinator.prompts import COORDINATOR_PROMPT
from agritwin_ai.agents.coordinator.tool_schema import TOOLS
from agritwin_ai.agents.coordinator.workflow import CoordinatorWorkflow


def test_coordinator_exposes_all_implemented_specialists():
    assert set(TOOLS) == {
        "run_harvest",
        "run_climate",
        "run_market",
        "run_logistics",
    }
    engine = create_engine()
    assert set(engine.tools) == set(TOOLS)


def test_coordinator_prompt_does_not_ban_market_or_logistics():
    for tool_name in TOOLS:
        assert tool_name in COORDINATOR_PROMPT
    assert "NEVER attempt to call any other tool" not in COORDINATOR_PROMPT


def test_coordinator_keeps_outputs_from_multiple_specialists():
    workflow = CoordinatorWorkflow()
    workflow.handle_tool_result("run_harvest", "Harvest recommendation")
    workflow.handle_tool_result("run_climate", {"rain_probability": 20})
    workflow.handle_tool_result("run_market", {"decision": "HOLD"})
    workflow.handle_tool_result("run_logistics", {"distance_km": 38.0})

    assert set(workflow.state.agent_outputs) == set(TOOLS)
    assert workflow.state.completed_agents == ["harvest", "climate", "market", "logistics"]
    assert workflow.requires_decision("harvest_decision") is False


def test_coordinator_records_each_agent_only_once():
    workflow = CoordinatorWorkflow()
    workflow.handle_tool_result("run_market", {"decision": "HOLD"})
    workflow.handle_tool_result("run_market", {"decision": "SELL"})
    assert workflow.state.completed_agents == ["market"]
    assert workflow.state.agent_outputs["run_market"]["decision"] == "SELL"


def test_coordinator_can_continue_to_a_second_specialist_after_text_result():
    from copy import deepcopy
    from types import SimpleNamespace
    from unittest.mock import Mock

    from agritwin_ai.agents.coordinator.agent import create_engine

    tools = deepcopy(TOOLS)
    tools["run_harvest"]["function"] = lambda user_message: "Harvest agent: harvest window is suitable."
    tools["run_climate"]["function"] = lambda user_message: {"rain_probability": 10}
    engine = create_engine(tools)
    engine.pipeline.prepare = Mock(return_value=(
        SimpleNamespace(intent="market_analysis", updates={}, entities={}),
        [],
    ))
    engine.reasoning.think = Mock(side_effect=[
        ("harvest tool", {"type": "tool", "data": {"action": "run_harvest", "arguments": {"user_message": "Check harvest and weather"}}}),
        ("climate tool", {"type": "tool", "data": {"action": "run_climate", "arguments": {"user_message": "Check harvest and weather"}}}),
        ("Combined result", {"type": "final", "data": "Harvest is suitable and rain risk is low."}),
    ])

    result = engine.run("Check harvest and weather")

    assert result == "Harvest is suitable and rain risk is low."
    assert engine.state.tool_calls == 2
    assert engine.workflow.state.completed_agents == ["harvest", "climate"]


def test_coordinator_market_tool_uses_price_only_path_for_current_price(monkeypatch):
    from agritwin_ai.agents.coordinator import tools as coordinator_tools

    class FakeMarketRuntime:
        def get_current_price(self, commodity, market):
            return {"commodity": commodity, "market": market, "is_current": False}

        def run(self, **kwargs):
            raise AssertionError("Current-price-only query must not run market economics")

    monkeypatch.setattr(coordinator_tools, "_market_runtime", FakeMarketRuntime())
    result = coordinator_tools.run_market(
        "I just want the current market price for onions in Nashik mandi; don't calculate my profit"
    )
    assert result["market"] == "Nashik"
    assert result["is_current"] is False


def test_coordinator_market_tool_can_return_two_mandis(monkeypatch):
    from agritwin_ai.agents.coordinator import tools as coordinator_tools

    class FakeMarketRuntime:
        def get_current_price(self, commodity, market):
            return {"commodity": commodity, "market": market}

        def run(self, **kwargs):
            return kwargs

    monkeypatch.setattr(coordinator_tools, "_market_runtime", FakeMarketRuntime())
    result = coordinator_tools.run_market("current onion price in Nashik mandi or Lasangaon mandi")
    assert result["intent"] == "current_price_comparison"
    assert [item["market"] for item in result["results"]] == ["Nashik", "Lasalgaon"]
