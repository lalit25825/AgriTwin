from datetime import date

import pytest

from agritwin_ai.data.market.normalizer import MarketNormalizer


def test_normalizer_converts_canonical_record():
    normalizer = MarketNormalizer()

    record = normalizer.normalize(
        {
            "date": "2026-09-08",
            "state": "Maharashtra",
            "district": "Nashik",
            "market": "Lasalgaon",
            "commodity": "Onion",
            "variety": "Onion",
            "grade": "FAQ",
            "arrival_quantity": "1,200",
            "min_price": "1800",
            "max_price": "2400",
            "modal_price": "2200",
        },
        source="ogd",
    )

    assert record.date == date(2026, 9, 8)
    assert record.arrival_quantity == 1200
    assert record.modal_price == 2200


def test_normalizer_supports_common_aliases():
    normalizer = MarketNormalizer()

    record = normalizer.normalize(
        {
            "arrival_date": "08/09/2026",
            "state_name": "Maharashtra",
            "district_name": "Nashik",
            "market_name": "Lasalgaon",
            "commodity_name": "Onion",
            "variety_name": "Onion",
            "grade_name": "FAQ",
            "arrival": "1200",
            "minimum_price": "1800",
            "maximum_price": "2400",
            "modal": "2200",
        },
        source="ogd",
    )

    assert record.date == date(2026, 9, 8)
    assert record.market == "Lasalgaon"
    assert record.min_price == 1800
    assert record.max_price == 2400


def test_normalizer_handles_optional_empty_values():
    normalizer = MarketNormalizer()

    record = normalizer.normalize(
        {
            "date": "2026-09-08",
            "state": "Maharashtra",
            "district": "   ",
            "market": "Lasalgaon",
            "commodity": "Onion",
            "variety": "",
            "grade": "   ",
            "arrival_quantity": 100,
            "min_price": 1000,
            "max_price": 1200,
            "modal_price": 1100,
        },
        source="ogd",
    )

    assert record.district is None
    assert record.variety is None
    assert record.grade is None


def test_normalizer_rejects_invalid_date():
    normalizer = MarketNormalizer()

    with pytest.raises(ValueError):
        normalizer.normalize(
            {
                "date": "not-a-date",
                "state": "Maharashtra",
                "market": "Lasalgaon",
                "commodity": "Onion",
                "arrival_quantity": 100,
                "min_price": 1000,
                "max_price": 1200,
                "modal_price": 1100,
            },
            source="ogd",
        )


def test_normalizer_rejects_invalid_numeric_value():
    normalizer = MarketNormalizer()

    with pytest.raises(ValueError):
        normalizer.normalize(
            {
                "date": "2026-09-08",
                "state": "Maharashtra",
                "market": "Lasalgaon",
                "commodity": "Onion",
                "arrival_quantity": "abc",
                "min_price": 1000,
                "max_price": 1200,
                "modal_price": 1100,
            },
            source="ogd",
        )


def test_normalizer_rejects_empty_source():
    normalizer = MarketNormalizer()

    with pytest.raises(ValueError):
        normalizer.normalize(
            {
                "date": "2026-09-08",
                "state": "Maharashtra",
                "market": "Lasalgaon",
                "commodity": "Onion",
                "arrival_quantity": 100,
                "min_price": 1000,
                "max_price": 1200,
                "modal_price": 1100,
            },
            source="   ",
        )