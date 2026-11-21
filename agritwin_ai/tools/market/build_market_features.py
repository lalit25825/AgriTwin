from __future__ import annotations

from pathlib import Path

import pandas as pd

from agritwin_ai.data.market.features import (
    MarketFeatureBuilder,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

HISTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "market"
    / "processed"
    / "market_history.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "market"
    / "processed"
    / "market_features.csv"
)


def main() -> None:
    print("=" * 70)
    print("AgriTwin Market Feature Builder")
    print("=" * 70)

    print("\nInput:")
    print(HISTORY_PATH)

    if not HISTORY_PATH.exists():
        raise FileNotFoundError(
            f"Historical dataset not found: "
            f"{HISTORY_PATH}"
        )

    dataframe = pd.read_csv(
        HISTORY_PATH
    )

    print(
        f"\nHistorical observations: "
        f"{len(dataframe)}"
    )

    print(
        f"Historical dates: "
        f"{dataframe['date'].nunique()}"
    )

    builder = MarketFeatureBuilder()

    print("\nBuilding features...")

    features = builder.build(
        dataframe
    )

    features.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        f"\nFeature dataset saved:"
    )
    print(OUTPUT_PATH)

    print(
        f"\nTotal feature rows: "
        f"{len(features)}"
    )

    print(
        f"Training-ready rows: "
        f"{features['training_ready'].sum()}"
    )

    print(
        f"Rows with lag_7: "
        f"{features['has_lag_7'].sum()}"
    )

    print(
        f"Rows with lag_30: "
        f"{features['has_lag_30'].sum()}"
    )

    print("\nFeature columns:")

    for column in builder.training_columns():
        print(f"  - {column}")

    print("\n" + "=" * 70)
    print("MARKET FEATURE BUILD COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()