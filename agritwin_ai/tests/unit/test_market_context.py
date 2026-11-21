import numpy as np
import pandas as pd
import pytest

from agritwin_ai.agents.market.market_context import (
    MarketContextBuilder,
)


def make_dataframe():
    return pd.DataFrame(
        {
            "date": pd.date_range(
                "2026-01-01",
                periods=5,
                freq="D",
            ),
            "commodity": [
                "Onion"
            ] * 5,
            "market": [
                "Lasalgaon"
            ] * 5,
            "modal_price": [
                1800,
                1820,
                1810,
                1850,
                1900,
            ],
        }
    )


def test_context_builder():
    builder = MarketContextBuilder()

    result = builder.build(
        make_dataframe(),
        "Onion",
        "Lasalgaon",
    )

    assert result["commodity"] == "Onion"
    assert result["market"] == "Lasalgaon"
    assert result["current_price"] == 1900
    assert result["previous_price"] == 1850
    assert result["observations"] == 5


def test_context_calculates_price_change():
    builder = MarketContextBuilder()

    result = builder.build(
        make_dataframe(),
        "Onion",
        "Lasalgaon",
    )

    assert result["price_change_pct"] > 0


def test_missing_market_is_rejected():
    builder = MarketContextBuilder()

    with pytest.raises(ValueError):
        builder.build(
            make_dataframe(),
            "Tomato",
            "Lasalgaon",
        )


def test_empty_dataframe_is_rejected():
    builder = MarketContextBuilder()

    with pytest.raises(ValueError):
        builder.build(
            pd.DataFrame(),
            "Onion",
            "Lasalgaon",
        )