from datetime import date

import pandas as pd
import pytest

from agritwin_ai.data.market.csv_provider import (
    CSVMarketDataProvider,
)


def make_csv(tmp_path):
    path = tmp_path / "market.csv"

    dataframe = pd.DataFrame(
        {
            "Date": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
            ],
            "State": [
                "Maharashtra",
                "Maharashtra",
                "Maharashtra",
            ],
            "District": [
                "Nashik",
                "Nashik",
                "Nashik",
            ],
            "Market": [
                "Lasalgaon",
                "Lasalgaon",
                "Lasalgaon",
            ],
            "Commodity": [
                "Onion",
                "Onion",
                "Onion",
            ],
            "Min Price": [
                1700,
                1750,
                1800,
            ],
            "Max Price": [
                1900,
                1950,
                2000,
            ],
            "Modal Price": [
                1800,
                1850,
                1900,
            ],
        }
    )

    dataframe.to_csv(
        path,
        index=False,
    )

    return path


def test_csv_provider_loads_records(tmp_path):
    path = make_csv(tmp_path)

    provider = CSVMarketDataProvider(path)

    records = provider.fetch_latest()

    assert len(records) == 3

    assert records[0]["Commodity"] == "Onion"


def test_csv_provider_filters_date_range(tmp_path):
    path = make_csv(tmp_path)

    provider = CSVMarketDataProvider(path)

    records = provider.fetch_range(
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 2),
    )

    assert len(records) == 1

    assert records[0]["Date"] == "2026-01-02"


def test_invalid_date_range_is_rejected(tmp_path):
    path = make_csv(tmp_path)

    provider = CSVMarketDataProvider(path)

    with pytest.raises(ValueError):
        provider.fetch_range(
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 1),
        )


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        CSVMarketDataProvider(
            tmp_path / "missing.csv"
        )


def test_health_check(tmp_path):
    path = make_csv(tmp_path)

    provider = CSVMarketDataProvider(path)

    assert provider.health_check() is True