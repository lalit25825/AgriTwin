from __future__ import annotations

from typing import Any


class LogisticsEvaluator:
    """Deterministic logistics decision layer. No LLM decisions happen here."""

    def evaluate(self, workflow, intent: str) -> dict[str, Any]:
        state = workflow.state
        route = state.route or {}
        cost = state.cost or {}
        risk = state.risk or {}
        routes = route.get("routes") or []
        if not routes:
            return {"error": "No route data available."}

        primary = routes[0]
        risk_level = str(risk.get("level", "UNKNOWN"))

        if risk_level == "HIGH":
            decision = "REPLAN_OR_DELAY"
        elif risk_level == "MODERATE":
            decision = "PROCEED_WITH_CAUTION"
        else:
            decision = "PROCEED"

        return {
            "decision": decision,
            "commodity": state.commodity,
            "quantity_tons": state.quantity_tons,
            "origin": state.origin,
            "destination": state.destination,
            "route_provider": route.get("provider"),
            "traffic_aware": bool(route.get("traffic_aware")),
            "distance_km": primary.get("distance_km"),
            "eta_minutes": primary.get("duration_minutes"),
            "estimated_transport_cost_inr": cost.get("estimated_total_inr"),
            "estimated_cost_per_ton_inr": cost.get("estimated_cost_per_ton_inr"),
            "risk_level": risk_level,
            "risk_score": risk.get("score"),
            "risk_factors": risk.get("factors", []),
            "route_options": routes,
            "reason": _reason(decision, risk_level),
        }


def _reason(decision: str, risk_level: str) -> str:
    if decision == "REPLAN_OR_DELAY":
        return "The current logistics conditions contain material route, weather, or perishability risk."
    if decision == "PROCEED_WITH_CAUTION":
        return "The shipment is feasible, but the measured logistics risk requires monitoring and contingency planning."
    return "The measured route, cost, and logistics risk are within the configured operating thresholds."
