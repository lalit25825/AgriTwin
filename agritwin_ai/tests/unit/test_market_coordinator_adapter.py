import numpy as np
import pandas as pd

from agritwin_ai.agents.market.coordinator_adapter import (
    MarketCoordinatorAdapter,
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


def test_market_adapter_handles_market_intents():
    adapter = MarketCoordinatorAdapter()

    assert adapter.can_handle("market")
    assert adapter.can_handle("market_analysis")
    assert adapter.can_handle("price_forecast")
    assert adapter.can_handle("commodity_price")


def test_market_adapter_rejects_unrelated_intent():
    adapter = MarketCoordinatorAdapter()

    assert not adapter.can_handle("weather")
    assert not adapter.can_handle("harvest")
    assert not adapter.can_handle("disease")


def test_market_adapter_executes_agent():
    adapter = MarketCoordinatorAdapter()

    result = adapter.execute(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
        horizon=7,
    )

    assert result["agent"] == "market"
    assert len(result["forecast"]) == 7
    assert "decision" in result


def test_market_adapter_preserves_context():
    adapter = MarketCoordinatorAdapter()

    result = adapter.execute(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
        storage_available=True,
    )

    assert result["commodity"] == "Onion"
    assert result["market"] == "Lasalgaon"
    assert "context" in result
    assert "risk" in result