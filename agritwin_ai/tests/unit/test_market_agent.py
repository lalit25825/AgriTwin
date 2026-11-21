import pytest
import numpy as np
import pandas as pd

from agritwin_ai.agents.market.market_agent import (
    MarketAgent,
)


def make_dataframe(rows=80):
    dates = pd.date_range(
        "2026-01-01",
        periods=rows,
        freq="D",
    )

    prices = (
        1800
        + np.arange(rows) * 2
        + np.sin(np.arange(rows)) * 10
    )

    return pd.DataFrame(
        {
            "date": dates,
            "state": ["Maharashtra"] * rows,
            "district": ["Nashik"] * rows,
            "market": ["Lasalgaon"] * rows,
            "commodity": ["Onion"] * rows,
            "modal_price": prices,
            "arrival_quantity": (
                1000 + np.arange(rows) * 3
            ),
        }
    )


def test_market_agent_runs():
    result = MarketAgent().run(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
    )

    assert result["agent"] == "market"


def test_market_agent_contains_context():
    result = MarketAgent().run(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
    )

    assert "context" in result

    assert result["context"]["commodity"] == "Onion"
    assert result["context"]["market"] == "Lasalgaon"
    assert result["context"]["current_price"] > 0


def test_market_agent_contains_risk():
    result = MarketAgent().run(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
    )

    assert "risk" in result

    assert result["risk"]["risk_level"] in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }

    assert result["risk"]["volatility_pct"] >= 0


def test_market_agent_contains_forecast():
    result = MarketAgent().run(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
        horizon=7,
    )

    assert len(
        result["forecast"]
    ) == 7


def test_market_agent_contains_decision():
    result = MarketAgent().run(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
    )

    assert result["decision"]["action"] in {
        "SELL",
        "HOLD",
        "STORE",
        "REDIRECT",
    }


def test_market_agent_storage_context():
    result = MarketAgent().run(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
        storage_available=True,
    )

    assert "decision" in result

def test_market_agent_contains_economics():
    result = MarketAgent().run(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
    )

    assert "economics" in result

    assert (
        result["economics"]["current_price"]
        > 0
    )

    assert (
        result["economics"]["expected_price"]
        > 0
    )


def test_market_agent_uses_net_nearby_advantage():
    result = MarketAgent().run(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
        nearby_market_price=2200,
        transport_cost=50,
    )

    economics = result["economics"]

    assert (
        economics["nearby_market_price"]
        == 2200
    )

    assert economics["net_nearby_gain"] == pytest.approx(
        2200
        - economics["current_price"]
        - 50,
        abs=0.01,
    )


def test_market_agent_storage_economics():
    result = MarketAgent().run(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
        storage_available=True,
        storage_cost=100,
        expected_spoilage_pct=5,
    )

    assert (
        "storage_adjusted_price"
        in result["economics"]
    )