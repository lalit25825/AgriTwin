import pytest

from agritwin_ai.agents.market.market_economics import (
    MarketEconomicAnalyzer,
)


def test_expected_price_change():
    analyzer = MarketEconomicAnalyzer()

    result = analyzer.analyze(
        current_price=2000,
        expected_price=2200,
    )

    assert result["expected_price_change_pct"] == 10.0


def test_nearby_market_net_gain():
    analyzer = MarketEconomicAnalyzer()

    result = analyzer.analyze(
        current_price=2000,
        expected_price=2200,
        nearby_market_price=2300,
        transport_cost=150,
    )

    assert result["gross_nearby_gain"] == 300
    assert result["net_nearby_gain"] == 150
    assert result["net_nearby_gain_pct"] == 7.5


def test_storage_adjustment():
    analyzer = MarketEconomicAnalyzer()

    result = analyzer.analyze(
        current_price=2000,
        expected_price=2400,
        storage_cost=100,
        expected_spoilage_pct=10,
    )

    assert result["storage_adjusted_price"] == 2060


def test_zero_current_price_is_safe():
    analyzer = MarketEconomicAnalyzer()

    result = analyzer.analyze(
        current_price=0,
        expected_price=100,
        nearby_market_price=200,
    )

    assert result["expected_price_change_pct"] == 0.0
    assert result["net_nearby_gain_pct"] == 0.0


def test_negative_price_rejected():
    analyzer = MarketEconomicAnalyzer()

    with pytest.raises(ValueError):
        analyzer.analyze(
            current_price=-1,
            expected_price=100,
        )


def test_invalid_spoilage_rejected():
    analyzer = MarketEconomicAnalyzer()

    with pytest.raises(ValueError):
        analyzer.analyze(
            current_price=2000,
            expected_price=2200,
            expected_spoilage_pct=120,
        )