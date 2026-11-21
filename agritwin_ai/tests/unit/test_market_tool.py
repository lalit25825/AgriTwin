import numpy as np
import pandas as pd

from agritwin_ai.tools.market.market_tool import (
    MarketTool,
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


def test_market_tool_executes():
    tool = MarketTool()

    result = tool.execute(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
        horizon=7,
    )

    assert result["agent"] == "market"


def test_market_tool_returns_forecast():
    tool = MarketTool()

    result = tool.execute(
        dataframe=make_dataframe(),
        commodity="Onion",
        market="Lasalgaon",
        horizon=5,
    )

    assert len(result["forecast"]) == 5


def test_market_tool_returns_decision():
    tool = MarketTool()

    result = tool.execute(
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


def test_market_tool_health_check():
    tool = MarketTool()

    assert tool.health_check() is True