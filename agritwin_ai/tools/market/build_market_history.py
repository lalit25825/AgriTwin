from __future__ import annotations

from pathlib import Path

from agritwin_ai.data.market.historical_store import (
    MarketHistoricalStore,
)
from agritwin_ai.data.market.normalizer import (
    normalize_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_PATH = (
    PROJECT_ROOT
    / "data"
    / "market"
    / "raw"
    / "ogd_market_data.csv"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "market"
    / "processed"
)

NORMALIZED_PATH = (
    PROCESSED_DIR
    / "market_records.csv"
)

HISTORY_PATH = (
    PROCESSED_DIR
    / "market_history.csv"
)


def main() -> None:
    print("=" * 60)
    print("AgriTwin Market Historical Builder")
    print("=" * 60)

    print("\nRaw input:")
    print(RAW_PATH)

    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"Raw market data not found: {RAW_PATH}"
        )

    print("\n[1/3] Normalizing raw OGD data...")

    normalized = normalize_csv(
        RAW_PATH,
        NORMALIZED_PATH,
    )

    print(
        f"Normalized records: {len(normalized)}"
    )

    print(
        f"Canonical dataset saved: {NORMALIZED_PATH}"
    )

    print("\n[2/3] Updating historical store...")

    store = MarketHistoricalStore(
        HISTORY_PATH
    )

    result = store.append(
        normalized
    )

    print(
        f"Previous rows:        {result['previous_rows']}"
    )

    print(
        f"Incoming rows:        {result['incoming_rows']}"
    )

    print(
        f"New rows:             {result['new_rows']}"
    )

    print(
        f"Duplicates removed:   {result['duplicates_removed']}"
    )

    print(
        f"Final historical rows:{result['final_rows']}"
    )

    print("\n[3/3] Inspecting history...")

    history = store.load()

    if history.empty:
        raise RuntimeError(
            "Historical market store is empty."
        )

    print(
        f"Date range: "
        f"{history['date'].min()} → "
        f"{history['date'].max()}"
    )

    print(
        f"States:       {history['state'].nunique()}"
    )

    print(
        f"Commodities:  {history['commodity'].nunique()}"
    )

    print(
        f"Markets:      {history['market'].nunique()}"
    )

    print("\nSample:")

    print(
        history[
            [
                "date",
                "state",
                "market",
                "commodity",
                "modal_price",
            ]
        ]
        .head(5)
        .to_string(index=False)
    )

    print("\n" + "=" * 60)
    print("MARKET HISTORY BUILD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()