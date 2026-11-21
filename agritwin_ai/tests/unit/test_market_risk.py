import pytest

from agritwin_ai.agents.market.market_risk import (
    MarketRiskAnalyzer,
)


def test_low_volatility():
    analyzer = MarketRiskAnalyzer()

    result = analyzer.analyze(
        [
            1800,
            1802,
            1801,
            1803,
            1802,
        ]
    )

    assert result["risk_level"] == "LOW"
    assert result["volatility_pct"] >= 0


def test_high_volatility():
    analyzer = MarketRiskAnalyzer()

    result = analyzer.analyze(
        [
            1000,
            1400,
            900,
            1500,
            800,
        ]
    )

    assert result["risk_level"] == "HIGH"


def test_single_observation():
    analyzer = MarketRiskAnalyzer()

    result = analyzer.analyze(
        [2000]
    )

    assert result["volatility_pct"] == 0
    assert result["risk_level"] == "LOW"


def test_empty_prices_rejected():
    analyzer = MarketRiskAnalyzer()

    with pytest.raises(ValueError):
        analyzer.analyze([])


def test_negative_prices_rejected():
    analyzer = MarketRiskAnalyzer()

    with pytest.raises(ValueError):
        analyzer.analyze(
            [2000, -100]
        )