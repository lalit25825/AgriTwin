"""Per-browser-session AgriTwin runtimes.

The terminal application historically held one process-global AgentEngine per
agent. Reusing those globals from a web server would mix different users'
conversation memories. This manager builds isolated engines per session and
serializes turns within each session.
"""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from threading import Lock, RLock
from typing import Any

from agritwin_ai.agents.coordinator.agent import create_engine as create_coordinator_engine
from agritwin_ai.agents.coordinator.tool_schema import TOOLS as COORDINATOR_TOOLS
from agritwin_ai.agents.harvest.agent import create_engine as create_harvest_engine
from agritwin_ai.agents.climate.agent import create_engine as create_climate_engine
from agritwin_ai.agents.market.agent import create_engine as create_market_engine
from agritwin_ai.agents.logistics.agent import create_engine as create_logistics_engine


class SessionRuntime:
    """Owns one independent set of AgriTwin engines for a browser session."""

    def __init__(self, stakeholder_context: str = "") -> None:
        self.harvest = create_harvest_engine()
        self.climate = create_climate_engine()
        self.market = create_market_engine()
        self.logistics = create_logistics_engine()

        # Keep role-specific context in each engine's system prompt rather than
        # prefixing the user's message. This preserves the original request for
        # deterministic intent parsing and gives every specialist the same role context.
        self.stakeholder_context = stakeholder_context.strip()
        if self.stakeholder_context:
            for specialist in (self.harvest, self.climate, self.market, self.logistics):
                self._append_stakeholder_context(specialist, self.stakeholder_context)

        coordinator_tools = deepcopy(COORDINATOR_TOOLS)
        coordinator_tools["run_harvest"]["function"] = self._run_harvest
        coordinator_tools["run_climate"]["function"] = self._run_climate
        coordinator_tools["run_market"]["function"] = self._run_market
        coordinator_tools["run_logistics"]["function"] = self._run_logistics
        self.coordinator = create_coordinator_engine(coordinator_tools)
        if self.stakeholder_context:
            self._append_stakeholder_context(self.coordinator, self.stakeholder_context)

        self.lock = RLock()
        self.last_logistics_result: dict[str, Any] | None = None

    @staticmethod
    def _append_stakeholder_context(engine: Any, context: str) -> None:
        prompt = (
            f"{engine.prompt}\n\n"
            "AUTHENTICATED AGRITWIN STAKEHOLDER CONTEXT\n"
            f"{context}\n\n"
            "All active specialist agents remain available to this stakeholder. "
            "Use the stakeholder role to prioritize the advice, not to restrict agent access. "
            "Ask for missing operational details instead of guessing. Keep data provenance, "
            "freshness, estimates and provider limitations explicit."
        )
        engine.prompt = prompt
        engine.memory._system_message = {"role": "system", "content": prompt}
        history = getattr(engine.memory, "messages", [])
        engine.memory.messages = [engine.memory._system_message.copy(), *history[1:]]

    @staticmethod
    def _is_map_followup(message: str) -> bool:
        lowered = message.lower()
        phrases = (
            "open the map", "show me the map", "show map",
            "show me route", "show the route", "open route",
            "route on map", "show directions", "display the route",
        )
        return any(phrase in lowered for phrase in phrases)

    @staticmethod
    def _find_route_result(outputs: dict[str, Any]) -> dict[str, Any] | None:
        for output in outputs.values():
            if (
                isinstance(output, dict)
                and isinstance(output.get("maps_url"), str)
                and isinstance(output.get("route"), dict)
                and isinstance(output.get("origin"), dict)
                and isinstance(output.get("destination"), dict)
            ):
                return output
        return None

    def _route_map_response(self) -> dict[str, Any]:
        route_data = self.last_logistics_result or {}
        route = route_data.get("route") or {}
        routes = route.get("routes") or []
        primary = routes[0] if routes else {}
        origin = route_data.get("origin") or {}
        destination = route_data.get("destination") or {}
        return {
            "type": "route_map",
            "message": "Here is the route from your previous logistics request.",
            "origin": origin.get("display_name") or origin.get("query"),
            "destination": destination.get("display_name") or destination.get("query"),
            "distance_km": primary.get("distance_km"),
            "duration_minutes": primary.get("duration_minutes"),
            "route_provider": route.get("provider"),
            "traffic_aware": route.get("traffic_aware", False),
            "maps_url": route_data.get("maps_url"),
            "location_resolution": route_data.get("location_resolution"),
        }

    def _run_harvest(self, user_message: str) -> Any:
        return self.harvest.run(user_message)

    def _run_climate(self, user_message: str) -> Any:
        return self.climate.run(user_message)

    def _run_market(self, user_message: str) -> Any:
        return self.market.run(user_message)

    def _run_logistics(self, user_message: str) -> Any:
        result = self.logistics.run(user_message)
        raw_result = getattr(self.logistics.workflow, "last_analysis_result", None)
        if isinstance(raw_result, dict) and raw_result.get("maps_url"):
            self.last_logistics_result = raw_result
        return result

    def run(self, agent: str, message: str) -> tuple[Any, list[str], dict[str, Any]]:
        """Run one selected specialist or the coordinator workflow."""
        engine_by_agent = {
            "coordinator": self.coordinator,
            "harvest": self.harvest,
            "climate": self.climate,
            "market": self.market,
            "logistics": self.logistics,
        }
        engine = engine_by_agent[agent]

        with self.lock:
            # A map request after a successful route calculation is a
            # presentation follow-up, not a brand-new logistics task.
            if agent in {"coordinator", "logistics"} and self.last_logistics_result and self._is_map_followup(message):
                payload = self._route_map_response()
                return payload, ["logistics"], {"route_map": payload}

            result = engine.run(message)
            if agent == "coordinator":
                workflow_state = engine.workflow.state
                used = list(workflow_state.completed_agents)
                outputs = dict(workflow_state.agent_outputs)
                route_result = self._find_route_result(outputs)
                if route_result is not None:
                    self.last_logistics_result = route_result
            else:
                used = [agent]
                outputs = {}
                if agent == "logistics":
                    raw_result = getattr(engine.workflow, "last_analysis_result", None)
                    if isinstance(raw_result, dict) and raw_result.get("maps_url"):
                        self.last_logistics_result = raw_result
                workflow_state = getattr(engine.workflow, "state", None)
                if workflow_state is not None:
                    for attribute in ("decision", "current_weather", "forecast", "market_data"):
                        value = getattr(workflow_state, attribute, None)
                        if value is not None:
                            outputs[attribute] = value
            return result, used, outputs


class SessionManager:
    """Small bounded LRU cache of isolated agent runtimes."""

    def __init__(self, max_sessions: int = 128) -> None:
        self.max_sessions = max(1, max_sessions)
        self._sessions: OrderedDict[str, SessionRuntime] = OrderedDict()
        self._lock = Lock()

    def get(self, session_id: str, stakeholder_context: str = "") -> SessionRuntime:
        with self._lock:
            runtime = self._sessions.get(session_id)
            if runtime is None:
                runtime = SessionRuntime(stakeholder_context=stakeholder_context)
                self._sessions[session_id] = runtime
            else:
                self._sessions.move_to_end(session_id)

            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)
            return runtime


session_manager = SessionManager()
