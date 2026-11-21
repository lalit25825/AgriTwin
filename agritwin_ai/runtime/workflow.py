"""Contracts implemented by agent-owned request workflows."""

from __future__ import annotations

from typing import Any, Protocol


class AgentWorkflow(Protocol):
    """Minimal workflow contract consumed by the agent-independent runtime."""

    state: Any

    def load_memory(self, memory: dict[str, Any]) -> None: ...

    def reflect(self, intent: str) -> dict[str, Any]: ...

    def requires_decision(self, intent: str) -> bool: ...

    def handle_tool_result(self, action: str, result: dict[str, Any]) -> None: ...

    def ready_for_evaluation(self) -> bool: ...

    def set_decision(self, decision: dict[str, Any]) -> None: ...

    def complete(self) -> None: ...
