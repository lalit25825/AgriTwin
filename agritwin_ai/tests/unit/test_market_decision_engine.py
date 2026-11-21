import pytest

from agritwin_ai.agents.market.decision_engine import (
    MarketDecisionEngine,
)


def test_rising_price_with_storage_returns_store():
    engine = MarketDecisionEngine()

    result = engine.decide(
        current_price=2000,
        forecast_prices=[
            2050,
            2100,
            2160,
            2200,
        ],
        storage_available=True,
    )

    assert result.action == "STORE"

    assert (
        result.expected_price_change_pct
        > 0
    )

    assert result.confidence > 0


def test_rising_price_without_storage_returns_hold():
    engine = MarketDecisionEngine()

    result = engine.decide(
        current_price=2000,
        forecast_prices=[
            2050,
            2100,
            2160,
            2200,
        ],
        storage_available=False,
    )

    assert result.action == "HOLD"


def test_falling_price_returns_sell():
    engine = MarketDecisionEngine()

    result = engine.decide(
        current_price=2000,
        forecast_prices=[
            1950,
            1900,
            1850,
            1800,
        ],
    )

    assert result.action == "SELL"

    assert (
        result.expected_price_change_pct
        < 0
    )


def test_nearby_market_advantage_returns_redirect():
    engine = MarketDecisionEngine()

    result = engine.decide(
        current_price=2000,
        forecast_prices=[
            2000,
            2010,
            2020,
        ],
        nearby_market_advantage_pct=12,
    )

    assert result.action == "REDIRECT"

    assert (
        "NEARBY_MARKET_HAS_SIGNIFICANTLY_HIGHER_PRICE"
        in result.reasons
    )


def test_stable_market_returns_hold():
    engine = MarketDecisionEngine()

    result = engine.decide(
        current_price=2000,
        forecast_prices=[
            2002,
            2005,
            2003,
        ],
    )

    assert result.action == "HOLD"


def test_high_volatility_increases_risk():
    engine = MarketDecisionEngine()

    result = engine.decide(
        current_price=2000,
        forecast_prices=[
            2200,
            2250,
            2300,
        ],
        volatility_pct=25,
    )

    assert result.risk_level == "HIGH"


def test_confidence_is_bounded():
    engine = MarketDecisionEngine()

    result = engine.decide(
        current_price=2000,
        forecast_prices=[
            2500,
            2600,
            2700,
        ],
    )

    assert 0 <= result.confidence <= 0.95


def test_invalid_current_price_is_rejected():
    engine = MarketDecisionEngine()

    with pytest.raises(ValueError):
        engine.decide(
            current_price=0,
            forecast_prices=[2000],
        )


def test_empty_forecast_is_rejected():
    engine = MarketDecisionEngine()

    with pytest.raises(ValueError):
        engine.decide(
            current_price=2000,
            forecast_prices=[],
        )


def test_negative_forecast_is_rejected():
    engine = MarketDecisionEngine()

    with pytest.raises(ValueError):
        engine.decide(
            current_price=2000,
            forecast_prices=[1900, -50],
        )