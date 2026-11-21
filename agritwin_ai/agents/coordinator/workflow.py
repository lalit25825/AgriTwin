from typing import Any

from agritwin_ai.agents.coordinator.state import CoordinatorState
from agritwin_ai.agents.coordinator.reflection import CoordinatorReflection


class CoordinatorWorkflow:
    """Request-local state for coordinator orchestration."""

    DIRECT_INTENTS = {"greeting", "thanks", "farewell", "acknowledgement", "provide_information", "unknown"}
    ACTION_TO_AGENT = {
        "run_harvest": "harvest",
        "run_climate": "climate",
        "run_market": "market",
        "run_logistics": "logistics",
    }

    def __init__(self):
        self.state = CoordinatorState()
        self.reflection = CoordinatorReflection()
        self._last_intent: str | None = None

    def load_memory(self, memory: dict[str, Any]) -> None:
        # The coordinator keeps specialist context in conversation memory.
        return None

    def needs_information(self, intent: str) -> list[str]:
        return []

    def reflect(self, intent: str) -> dict[str, Any]:
        self._last_intent = intent
        return self.reflection.check(self, intent)

    def requires_decision(self, intent: str) -> bool:
        # Specialist agents own their deterministic decision engines. The
        # coordinator only gathers outputs and writes the cross-agent synthesis.
        return False

    def ready_for_evaluation(self) -> bool:
        return bool(self.state.agent_outputs)

    def handle_tool_result(self, action: str, result: Any) -> None:
        """Store every completed tool result and track specialist participation."""
        self.state.agent_outputs[action] = result
        agent_name = self.ACTION_TO_AGENT.get(action)
        if agent_name and agent_name not in self.state.completed_agents:
            self.state.completed_agents.append(agent_name)
        if agent_name and agent_name not in self.state.required_agents:
            self.state.required_agents.append(agent_name)

