from __future__ import annotations

from typing import Any


class MarketEvaluator:
    """
    Deterministic evaluator for the Market Agent.

    The actual market intelligence and recommendation are produced
    by MarketAgent. This evaluator extracts the deterministic
    decision from the completed Market workflow result.

    It never asks the LLM to make a market recommendation.
    """

    def evaluate(
        self,
        workflow: Any,
        intent: str,
    ) -> dict[str, Any]:

        market_data = workflow.state.market_data

        if not market_data:
            return {
                "error": "Market analysis data is unavailable."
            }

        decision = market_data.get("decision")

        if not isinstance(decision, dict):
            return {
                "error": "Deterministic market decision is unavailable."
            }

        result: dict[str, Any] = {
            "decision": decision.get(
                "decision"
            ),
            "confidence": decision.get(
                "confidence"
            ),
        }

        for key, value in decision.items():
            if key not in result:
                result[key] = value

        return result