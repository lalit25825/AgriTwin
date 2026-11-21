"""Normalize parsed LLM responses for the engine."""

from typing import Any, Optional


class ResponseHandler:
    """Return final text and tool-call data without decision logic."""

    def final(
        self,
        parsed: dict[str, Any],
        decision: Optional[dict[str, Any]] = None,
        decision_label: str = "",
    ) -> str:
        """Return an LLM explanation with the authoritative decision prefixed."""
        explanation = parsed["data"]
        if decision is None:
            return explanation
        action = decision.get("decision", decision.get("overall_risk", "available"))
        prefix = f"Deterministic {decision_label} decision".strip()
        return f"{prefix}: {action}\n\n{explanation}"

    def tool(self, parsed: dict[str, Any]) -> tuple[str, dict[str, Any]]:

        return (

            parsed["data"]["action"],

            parsed["data"]["arguments"]

        )
