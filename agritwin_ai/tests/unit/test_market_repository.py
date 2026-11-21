from datetime import date

import pytest

from agritwin_ai.data.market.repository import MarketRepository
from agritwin_ai.data.market.schema import MarketRecord


def make_record(
    *,
    observation_date=date(2026, 9, 8),
    commodity="Onion",
    market="Lasalgaon",
    modal_price=2200,
):
    return MarketRecord(
        date=observation_date,
        state="Maharashtra",
        district="Nashik",
        market=market,
        commodity=commodity,
        variety="Onion",
        grade="FAQ",
        arrival_quantity=1200,
        min_price=1800,
        max_price=2400,
        modal_price=modal_price,
        source="test",
    )


def test_repository_starts_empty(tmp_path):
    repository = MarketRepository(
        tmp_path / "market_records.csv"
    )

    assert repository.load() == []
    assert repository.count() == 0


def test_repository_saves_records(tmp_path):
    repository = MarketRepository(
        tmp_path / "market_records.csv"
    )

    records = [
        make_record(),
        make_record(
            observation_date=date(2026, 9, 9),
            modal_price=2300,
        ),
    ]

    inserted = repository.save(records)

    assert inserted == 2
    assert repository.count() == 2


def test_repository_loads_records(tmp_path):
    repository = MarketRepository(
        tmp_path / "market_records.csv"
    )

    original = make_record()

    repository.save([original])

    loaded = repository.load()

    assert len(loaded) == 1
    assert loaded[0].commodity == "Onion"
    assert loaded[0].market == "Lasalgaon"
    assert loaded[0].modal_price == 2200
    assert loaded[0].date == date(2026, 9, 8)


def test_repository_prevents_duplicates(tmp_path):
    repository = MarketRepository(
        tmp_path / "market_records.csv"
    )

    record = make_record()

    first_insert = repository.save([record])
    second_insert = repository.save([record])

    assert first_insert == 1
    assert second_insert == 0
    assert repository.count() == 1


def test_repository_queries_by_commodity(tmp_path):
    repository = MarketRepository(
        tmp_path / "market_records.csv"
    )

    repository.save(
        [
            make_record(commodity="Onion"),
            make_record(
                observation_date=date(2026, 9, 9),
                commodity="Potato",
            ),
        ]
    )

    results = repository.query(
        commodity="onion",
    )

    assert len(results) == 1
    assert results[0].commodity == "Onion"


def test_repository_queries_by_market(tmp_path):
    repository = MarketRepository(
        tmp_path / "market_records.csv"
    )

    repository.save(
        [
            make_record(market="Lasalgaon"),
            make_record(
                observation_date=date(2026, 9, 9),
                market="Pimpalgaon",
            ),
        ]
    )

    results = repository.query(
        market="pimpalgaon",
    )

    assert len(results) == 1
    assert results[0].market == "Pimpalgaon"


def test_repository_queries_by_date_range(tmp_path):
    repository = MarketRepository(
        tmp_path / "market_records.csv"
    )

    repository.save(
        [
            make_record(
                observation_date=date(2026, 9, 1),
            ),
            make_record(
                observation_date=date(2026, 9, 5),
            ),
            make_record(
                observation_date=date(2026, 9, 10),
            ),
        ]
    )

    results = repository.query(
        start_date=date(2026, 9, 3),
        end_date=date(2026, 9, 7),
    )

    assert len(results) == 1
    assert results[0].date == date(2026, 9, 5)


def test_repository_rejects_non_market_record(tmp_path):
    repository = MarketRepository(
        tmp_path / "market_records.csv"
    )

    with pytest.raises(TypeError):
        repository.save(
            [{"commodity": "Onion"}]
        )


def test_repository_creates_parent_directory(tmp_path):
    path = (
        tmp_path
        / "nested"
        / "processed"
        / "market.csv"
    )

    repository = MarketRepository(path)

    repository.save([make_record()])

    assert path.exists()