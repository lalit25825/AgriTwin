from __future__ import annotations

from datetime import date as real_date

import pandas as pd

from agritwin_ai.agents.harvest.evaluator import HarvestEvaluator
from agritwin_ai.agents.harvest.state import HarvestState
from agritwin_ai.agents.logistics import tools as logistics_tools
from agritwin_ai.agents.logistics.providers import GeoPoint
from agritwin_ai.agents.market.market_runtime import MarketRuntime
from agritwin_ai.agents.market.tool_schema import TOOLS as MARKET_TOOLS
from agritwin_ai.agents.market.workflow import MarketWorkflow
from agritwin_ai.runtime.conversation_resolver import ConversationResolver
from agritwin_ai.understanding.validator import validate_tool
from agritwin_ai.web.session_manager import SessionRuntime


def test_market_forecast_does_not_require_profit_inputs():
    assert validate_tool(
        "get_market_analysis",
        {"commodity": "Onion", "market": "Lasalgaon"},
        MARKET_TOOLS,
    ) == (True, None)


def test_market_workflow_uses_city_as_market_without_horizon():
    workflow = MarketWorkflow()
    workflow.load_memory({"commodity": "onion", "city": "Nashik"})
    assert workflow.state.market == "Nashik"


def test_price_lookup_marks_old_snapshot_as_historical(tmp_path, monkeypatch):
    frame = pd.DataFrame({
        "date": ["2026-09-09", "2026-09-09"],
        "commodity": ["Onion", "Onion"],
        "market": ["Lasalgaon", "Lasalgaon"],
        "modal_price": [2500, 2550],
    })
    path = tmp_path / "market.csv"
    frame.to_csv(path, index=False)

    class FixedDate:
        @classmethod
        def today(cls):
            return real_date(2026, 11, 18)

    monkeypatch.setattr("agritwin_ai.agents.market.market_runtime.date", FixedDate)
    result = MarketRuntime(data_path=path).get_current_price("Onion", "Lasalgaon")

    assert result["current_price"] == 2525.0
    assert result["last_date"] == "2026-09-09"
    assert result["is_current"] is False
    assert result["freshness"] == "stale_snapshot"
    assert "not today's live price" in result["warning"]


def test_market_clarification_preserves_previous_onion_price_task():
    resolver = ConversationResolver()
    history = [
        {"role": "user", "content": "What will onion prices be next week?"},
        {"role": "assistant", "content": "Which mandi do you want?"},
    ]
    resolved = resolver.resolve(
        history,
        {"crop": "onion"},
        "Nashik mandi or Lasalgaon mandi",
    )
    assert "What will onion prices be next week?" in resolved
    assert "Nashik mandi or Lasalgaon mandi" in resolved


def test_new_harvest_request_is_not_misread_as_market_clarification():
    resolver = ConversationResolver()
    history = [
        {"role": "user", "content": "What is the onion market price in Nashik?"},
        {"role": "assistant", "content": "Which mandi do you mean?"},
    ]
    resolved = resolver.resolve(
        history,
        {"crop": "onion", "market": "Nashik"},
        "Should I harvest my onions day after tomorrow?",
    )
    assert "Previous task:" not in resolved
    assert resolved == "Should I harvest my onions day after tomorrow?"


def test_harvest_evaluator_recognizes_day_after_tomorrow_token():
    evaluator = HarvestEvaluator()
    assert evaluator._days_needed_from_date_string("day_after_tomorrow") == 2


def test_specific_harvest_date_evaluates_only_requested_day():
    evaluator = HarvestEvaluator()
    workflow = type("Workflow", (), {})()
    workflow.state = HarvestState()
    workflow.state.date = "day_after_tomorrow"
    workflow.state.crop_info = {
        "rain_sensitive": True,
        "max_humidity": 70,
        "ideal_temperature": {"min": 18, "max": 25},
        "ideal_wind_speed": 20,
    }
    workflow.state.forecast = {"forecast": [
        {"date": "2026-11-18", "temperature_min": 17, "temperature_max": 29,
         "humidity": 45, "rain_probability": 0, "wind_speed": 12},
        {"date": "2026-11-19", "temperature_min": 15, "temperature_max": 28,
         "humidity": 42, "rain_probability": 0, "wind_speed": 15},
        {"date": "2026-11-20", "temperature_min": 14.3, "temperature_max": 27.2,
         "humidity": 43, "rain_probability": 0, "wind_speed": 12.1},
    ]}

    result = evaluator.evaluate(workflow, "harvest_decision")

    assert result["requested_date"] == "2026-11-20"
    assert result["evaluation_scope"] == "requested_date_only"
    assert result["best_day"] == "2026-11-20"
    assert result["weather_summary"]["temperature_average_c"] == 20.75
    assert result["weather_summary"]["temperature_min_c"] == 14.3
    assert result["weather_summary"]["temperature_max_c"] == 27.2


def test_lasangaon_from_nashik_prefers_lasalgaon_local_candidate(monkeypatch):
    origin = GeoPoint(
        query="Nashik",
        latitude=20.0112,
        longitude=73.7902,
        display_name="Nashik, Maharashtra, India",
    )
    madhya_pradesh_result = GeoPoint(
        query="Lasangaon",
        latitude=22.1641,
        longitude=75.5036,
        display_name="Lasangaon, Dhar, Madhya Pradesh, India",
    )
    local_result = GeoPoint(
        query="Lasalgaon, Niphad, Nashik, Maharashtra, India",
        latitude=20.145,
        longitude=74.2,
        display_name="Lasalgaon, Niphad, Nashik, Maharashtra, India",
    )

    class FakeGeocoder:
        def geocode(self, query):
            if query == "Lasangaon":
                return madhya_pradesh_result
            if query == "Lasalgaon, Niphad, Nashik, Maharashtra, India":
                return local_result
            raise AssertionError(f"Unexpected geocode query: {query}")

    monkeypatch.setattr(logistics_tools, "_geocoder", FakeGeocoder())
    resolved = logistics_tools._resolve_destination("Lasangaon", "Nashik", origin)
    assert resolved == local_result


def test_map_followup_reuses_previous_logistics_route():
    runtime = SessionRuntime()
    runtime.last_logistics_result = {
        "origin": {"query": "Nashik", "display_name": "Nashik, Maharashtra, India"},
        "destination": {"query": "Lasalgaon", "display_name": "Lasalgaon, Nashik, Maharashtra, India"},
        "route": {
            "provider": "OSRM",
            "traffic_aware": False,
            "routes": [{"distance_km": 64.2, "duration_minutes": 75.0}],
        },
        "maps_url": "https://www.google.com/maps/dir/?api=1&origin=20.01%2C73.79&destination=20.14%2C74.2&travelmode=driving",
        "location_resolution": {"destination_was_interpreted": True, "destination_resolved": "Lasalgaon"},
    }

    result, agents, observations = runtime.run("coordinator", "open the map and show me route")

    assert result["type"] == "route_map"
    assert result["distance_km"] == 64.2
    assert result["duration_minutes"] == 75.0
    assert result["maps_url"].startswith("https://www.google.com/maps/dir/")
    assert agents == ["logistics"]
    assert "route_map" in observations


def test_market_price_planner_splits_two_mandis_into_separate_lookups():
    from agritwin_ai.runtime.planner import Planner
    from agritwin_ai.understanding.schema import UnderstandingResult

    workflow = MarketWorkflow()
    workflow.load_memory({"commodity": "onion", "market": "Nashik or Lasalgaon"})
    understanding = UnderstandingResult(
        intent="market_price",
        entities={"crop": "onion", "market": "Nashik or Lasalgaon"},
    )

    plan = Planner().plan(
        understanding,
        workflow,
        {"commodity": "onion", "market": "Nashik or Lasalgaon"},
    )

    assert [action.name for action in plan.actions] == [
        "get_market_price", "get_market_price"
    ]
    assert [action.arguments["market"] for action in plan.actions] == [
        "Nashik", "Lasalgaon"
    ]


def test_market_forecast_planner_splits_two_mandis():
    from agritwin_ai.runtime.planner import Planner
    from agritwin_ai.understanding.schema import UnderstandingResult

    workflow = MarketWorkflow()
    workflow.load_memory({"commodity": "onion", "market": "Nashik or Lasalgaon"})
    understanding = UnderstandingResult(
        intent="price_forecast",
        entities={"crop": "onion", "market": "Nashik or Lasalgaon", "quantity": 14},
    )

    plan = Planner().plan(
        understanding,
        workflow,
        {"commodity": "onion", "market": "Nashik or Lasalgaon"},
    )

    assert [action.name for action in plan.actions] == [
        "get_market_analysis", "get_market_analysis"
    ]
    assert [action.arguments["market"] for action in plan.actions] == [
        "Nashik", "Lasalgaon"
    ]


def test_current_price_override_discards_pending_forecast_date():
    resolver = ConversationResolver()
    history = [
        {"role": "user", "content": "What will onion prices be next week and up to 25 Nov 2026?"},
        {"role": "assistant", "content": "Which mandi do you want?"},
    ]
    resolved = resolver.resolve(
        history,
        {"crop": "onion", "market": "Nashik or Lasalgaon", "date": "2026-11-25"},
        "I just want the price, not profit, and the current market price.",
    )

    assert "current observed market price" in resolved
    assert "onion" in resolved
    assert "Nashik or Lasalgaon" in resolved
    assert "25 Nov 2026" not in resolved
    assert "supersedes earlier future forecast dates" in resolved


def test_direct_logistics_mode_caches_route_for_map_followup():
    from types import SimpleNamespace

    runtime = SessionRuntime()
    route = {
        "origin": {"query": "Nashik", "display_name": "Nashik, Maharashtra, India"},
        "destination": {"query": "Lasalgaon", "display_name": "Lasalgaon, Nashik, Maharashtra, India"},
        "route": {"provider": "OSRM", "traffic_aware": False, "routes": [{"distance_km": 64.2, "duration_minutes": 75.0}]},
        "maps_url": "https://www.google.com/maps/dir/?api=1&origin=20.01%2C73.79&destination=20.14%2C74.2&travelmode=driving",
    }
    runtime.logistics = SimpleNamespace(
        run=lambda message: "Route calculated.",
        workflow=SimpleNamespace(last_analysis_result=route, state=None),
    )

    result, agents, _ = runtime.run("logistics", "route from Nashik to Lasalgaon")

    assert result == "Route calculated."
    assert runtime.last_logistics_result is route
    map_result, _, _ = runtime.run("logistics", "open the map and show me route")
    assert map_result["type"] == "route_map"
    assert map_result["distance_km"] == 64.2
