
"""
Validated tool execution adapter.
"""

from __future__ import annotations

from typing import Any

from agritwin_ai.runtime.executor import execute_tool
from agritwin_ai.understanding.validator import validate_tool


class ToolExecutor:
    """
    Validate and execute tools registered by an agent.
    """

    def __init__(
        self,
        tools: dict[str, dict[str, Any]],
    ) -> None:
        self.tools = tools

    def execute(
        self,
        action: str,
        arguments: dict[str, Any],
    ) -> tuple[bool, Any]:

        valid, error = validate_tool(
            action,
            arguments,
            self.tools,
        )

        if not valid:
            return False, error

        result = execute_tool(
            action,
            arguments,
            self.tools,
        )

        # executor.py represents execution failures as dictionaries
        # containing an "error" field.
        if isinstance(result, dict) and "error" in result:
            return False, result

        return True, result
