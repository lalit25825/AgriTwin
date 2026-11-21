from __future__ import annotations

from pathlib import Path

import pandas as pd

from agritwin_ai.data.market.ogd_provider import OGDMarketDataProvider


OUTPUT = Path("data/market/raw/ogd_market_data.csv")


DEDUP_COLUMNS = [
    "state",
    "district",
    "market",
    "commodity",
    "variety",
    "grade",
    "arrival_date",
]


def validate_records(
    records: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    Validate OGD records.

    Returns:
        valid_records, invalid_records

    Invalid records are retained separately so that ingestion
    never silently loses data or corrupts the canonical dataset.
    """

    required_columns = {
        "state",
        "district",
        "market",
        "commodity",
        "variety",
        "grade",
        "arrival_date",
        "min_price",
        "max_price",
        "modal_price",
    }

    valid_records: list[dict] = []
    invalid_records: list[dict] = []

    for index, record in enumerate(records):

        missing = required_columns - set(record.keys())

        if missing:
            invalid_records.append(
                {
                    **record,
                    "_validation_error": (
                        f"missing fields: {sorted(missing)}"
                    ),
                    "_record_index": index,
                }
            )
            continue

        try:
            minimum = float(record["min_price"])
            maximum = float(record["max_price"])
            modal = float(record["modal_price"])

        except (TypeError, ValueError):
            invalid_records.append(
                {
                    **record,
                    "_validation_error": "non-numeric price",
                    "_record_index": index,
                }
            )
            continue

        if minimum < 0:
            invalid_records.append(
                {
                    **record,
                    "_validation_error": "min_price < 0",
                    "_record_index": index,
                }
            )
            continue

        if maximum < 0:
            invalid_records.append(
                {
                    **record,
                    "_validation_error": "max_price < 0",
                    "_record_index": index,
                }
            )
            continue

        if modal < 0:
            invalid_records.append(
                {
                    **record,
                    "_validation_error": "modal_price < 0",
                    "_record_index": index,
                }
            )
            continue

        if maximum < minimum:
            invalid_records.append(
                {
                    **record,
                    "_validation_error": (
                        "max_price < min_price"
                    ),
                    "_record_index": index,
                }
            )
            continue

        if modal < minimum:
            invalid_records.append(
                {
                    **record,
                    "_validation_error": (
                        "modal_price < min_price"
                    ),
                    "_record_index": index,
                }
            )
            continue

        if modal > maximum:
            invalid_records.append(
                {
                    **record,
                    "_validation_error": (
                        "modal_price > max_price"
                    ),
                    "_record_index": index,
                }
            )
            continue

        valid_records.append(record)

    return valid_records, invalid_records

def clean_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    dataframe = dataframe.copy()

    dataframe["state"] = (
        dataframe["state"]
        .astype(str)
        .str.strip()
    )

    dataframe["district"] = (
        dataframe["district"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    dataframe["market"] = (
        dataframe["market"]
        .astype(str)
        .str.strip()
    )

    dataframe["commodity"] = (
        dataframe["commodity"]
        .astype(str)
        .str.strip()
    )

    dataframe["variety"] = (
        dataframe["variety"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    dataframe["grade"] = (
        dataframe["grade"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    dataframe["arrival_date"] = pd.to_datetime(
        dataframe["arrival_date"],
        dayfirst=True,
        errors="coerce",
    )

    price_columns = [
        "min_price",
        "max_price",
        "modal_price",
    ]

    for column in price_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe = dataframe.dropna(
        subset=[
            "state",
            "market",
            "commodity",
            "arrival_date",
            "min_price",
            "max_price",
            "modal_price",
        ]
    )

    dataframe = dataframe[
        (dataframe["min_price"] >= 0)
        & (dataframe["max_price"] >= 0)
        & (dataframe["modal_price"] >= 0)
        & (
            dataframe["max_price"]
            >= dataframe["min_price"]
        )
        & (
            dataframe["modal_price"]
            >= dataframe["min_price"]
        )
        & (
            dataframe["modal_price"]
            <= dataframe["max_price"]
        )
    ]

    before = len(dataframe)

    dataframe = dataframe.drop_duplicates(
        subset=DEDUP_COLUMNS,
        keep="first",
    )

    duplicates_removed = before - len(dataframe)

    print(
        f"\nDuplicate records removed: "
        f"{duplicates_removed}"
    )

    dataframe = dataframe.sort_values(
        by=[
            "arrival_date",
            "state",
            "market",
            "commodity",
        ]
    ).reset_index(drop=True)

    dataframe["arrival_date"] = (
        dataframe["arrival_date"]
        .dt.strftime("%d/%m/%Y")
    )

    return dataframe


def main() -> None:

    print("=" * 70)
    print("AgriTwin LIVE OGD MARKET DATA DOWNLOAD")
    print("=" * 70)

    provider = OGDMarketDataProvider()

    print("\nFetching state-partitioned dataset...")

    records = provider.fetch_all_partitioned(
        page_size=1000,
    )

    print(
        f"\nRaw records downloaded: "
        f"{len(records)}"
    )

    valid_records, invalid_records = validate_records(
        records
    )

    print(
        f"\nValid records: "
        f"{len(valid_records)}"
    )

    print(
        f"Invalid records: "
        f"{len(invalid_records)}"
    )

    if invalid_records:
        quarantine_path = Path(
            "data/market/raw/ogd_invalid_records.csv"
        )

        quarantine_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        pd.DataFrame(
            invalid_records
        ).to_csv(
            quarantine_path,
            index=False,
            encoding="utf-8",
        )

        print(
            f"\nInvalid records quarantined to:"
        )
        print(quarantine_path)

    dataframe = pd.DataFrame(
        valid_records
    )

    print("\nCleaning and validating dataset...")

    dataframe = clean_dataframe(dataframe)

    if dataframe.empty:
        raise RuntimeError(
            "Cleaned market dataset is empty."
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        OUTPUT,
        index=False,
        encoding="utf-8",
    )

    print(
        f"\nFinal clean records: "
        f"{len(dataframe)}"
    )

    print(
        f"\nSaved to:\n{OUTPUT}"
    )

    print("\nStates:")
    for state in sorted(
        dataframe["state"].unique()
    ):
        count = int(
            (
                dataframe["state"]
                == state
            ).sum()
        )

        print(
            f"  {state}: {count}"
        )

    print("\nDate range:")

    dates = pd.to_datetime(
        dataframe["arrival_date"],
        dayfirst=True,
    )

    print(
        f"  Earliest: "
        f"{dates.min().strftime('%d/%m/%Y')}"
    )

    print(
        f"  Latest:   "
        f"{dates.max().strftime('%d/%m/%Y')}"
    )

    print("\nCommodities:")
    print(
        f"  Unique commodities: "
        f"{dataframe['commodity'].nunique()}"
    )

    print("\nMarkets:")
    print(
        f"  Unique markets: "
        f"{dataframe['market'].nunique()}"
    )

    print("\nSample:")
    print(
        dataframe.head(10).to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("CLEAN OGD MARKET DATA DOWNLOAD COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()