from datetime import date

import pytest
from pydantic import ValidationError

from agritwin_ai.data.market.schema import MarketRecord


def make_record(**overrides):
    data = {
        "date": date(2026, 9, 8),
        "state": "Maharashtra",
        "district": "Nashik",
        "market": "Lasalgaon",
        "commodity": "Onion",
        "variety": "Onion",
        "grade": "FAQ",
        "arrival_quantity": 1200,
        "min_price": 1800,
        "max_price": 2400,
        "modal_price": 2200,
        "source": "test",
    }

    data.update(overrides)

    return MarketRecord(**data)


def test_market_record_creation():
    record = make_record()

    assert record.commodity == "Onion"
    assert record.market == "Lasalgaon"
    assert record.modal_price == 2200


def test_prices_must_be_non_negative():
    with pytest.raises(ValidationError):
        make_record(min_price=-1)


def test_arrival_quantity_must_be_non_negative():
    with pytest.raises(ValidationError):
        make_record(arrival_quantity=-100)


def test_max_price_cannot_be_less_than_min_price():
    with pytest.raises(ValidationError):
        make_record(
            min_price=2500,
            max_price=2000,
            modal_price=2200,
        )


def test_modal_price_must_be_inside_price_range():
    with pytest.raises(ValidationError):
        make_record(modal_price=3000)


def test_empty_required_text_is_rejected():
    with pytest.raises(ValidationError):
        make_record(commodity="")


def test_optional_empty_text_becomes_none():
    record = make_record(
        district="   ",
        variety="",
        grade="   ",
    )

    assert record.district is None
    assert record.variety is None
    assert record.grade is None


def test_record_serializes_to_dict():
    record = make_record()

    data = record.model_dump()

    assert data["commodity"] == "Onion"
    assert data["market"] == "Lasalgaon"
    assert data["modal_price"] == 2200


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        make_record(unexpected_field="bad")