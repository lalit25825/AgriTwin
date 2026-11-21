from backend.app.agents.equity_agent import run as run_equity
from backend.app.agents.harvesting_agent import run as run_harvesting
from backend.app.agents.market_agent import _normalise_record, _trend_forecast
from backend.app.agents.schemas import AgentRunRequest
from backend.app.agents.storage_agent import run as run_storage


def test_harvesting_agent_does_not_claim_unknown_crop_is_ready():
    result = run_harvesting(AgentRunRequest(crop="Soybean"))
    assert result["status"] == "completed"
    assert result["data"]["readiness"] == "not_confirmed"
    assert "crop stage" in result["summary"].lower()


def test_harvesting_agent_marks_ready_stage_for_verification():
    result = run_harvesting(AgentRunRequest(crop="Wheat", crop_stage="ready"))
    assert result["data"]["readiness"] == "ready_to_verify"
    assert "confirm" in result["summary"].lower()


def test_storage_agent_returns_crop_specific_advice():
    result = run_storage(AgentRunRequest(crop="Soybean", quantity_tonnes=8))
    assert result["status"] == "completed"
    assert "moisture" in result["summary"].lower()
    assert result["data"]["quantity_tonnes"] == 8


def test_equity_agent_calculates_indicative_margin_and_gross_value():
    request = AgentRunRequest(
        crop="Soybean",
        quantity_tonnes=12,
        expected_sale_price=4500,
        production_cost_per_quintal=3200,
    )
    result = run_equity(request)
    assert result["data"]["estimated_margin_inr_per_quintal"] == 1300
    assert result["data"]["quantity_quintals"] == 120
    assert result["data"]["gross_value_inr_before_costs"] == 540000


def test_market_record_normalisation_and_trend_projection():
    record = _normalise_record({
        "Commodity": "Soybean",
        "Market": "Lasalgaon",
        "Arrival_Date": "20/11/2026",
        "Modal_Price": "4,500",
    })
    assert record["arrival_date"] == "2026-11-20"
    assert record["modal_price"] == 4500

    forecast = _trend_forecast([
        {"date": "2026-11-17", "modal_price": 4000},
        {"date": "2026-11-18", "modal_price": 4100},
        {"date": "2026-11-19", "modal_price": 4200},
    ])
    assert len(forecast) == 3
    assert forecast[0]["projected_modal_price"] > 4200
