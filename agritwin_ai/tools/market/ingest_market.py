from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agritwin_ai.data.market.collector import MarketDataCollector
from agritwin_ai.data.market.csv_provider import CSVMarketDataProvider
from agritwin_ai.data.market.profiler import MarketDataProfiler
from agritwin_ai.data.market.repository import MarketRepository
from agritwin_ai.data.market.ingestion import MarketIngestionService


DEFAULT_OUTPUT = Path(
    "data/market/processed/market_records.csv"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest official agricultural mandi market data."
    )

    parser.add_argument(
        "--csv",
        required=True,
        help="Path to the downloaded OGD/AGMARKNET CSV file.",
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Destination for normalized market records.",
    )

    parser.add_argument(
        "--no-raw",
        action="store_true",
        help="Do not save the original raw records.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    csv_path = Path(args.csv)

    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        return 1

    print("=" * 70)
    print("AgriTwin Market Data Ingestion")
    print("=" * 70)

    print(f"\nSource : {csv_path}")
    print(f"Output : {args.output}")

    try:
        provider = CSVMarketDataProvider(csv_path)

        collector = MarketDataCollector(
            provider=provider,
            raw_directory="data/market/raw",
        )

        repository = MarketRepository(
            path=args.output,
        )

        service = MarketIngestionService(
            collector=collector,
            repository=repository,
        )

        result = service.ingest_latest(
            save_raw=not args.no_raw,
        )

        print("\n--- INGESTION RESULT ---")
        print(f"Fetched       : {result['fetched']}")
        print(f"Inserted      : {result['inserted']}")
        print(f"Duplicates    : {result['duplicates']}")
        print(f"Date range    : {result['date_min']} → {result['date_max']}")
        print(f"Commodities   : {len(result['commodities'])}")
        print(f"Markets       : {len(result['markets'])}")

        print("\n--- DATA PROFILE ---")

        dataframe = collector.normalizer

        import pandas as pd

        loaded = pd.read_csv(args.output)

        profiler = MarketDataProfiler()

        profile = profiler.profile(loaded)
        coverage = profiler.coverage_report(loaded)

        print(f"Rows          : {profile['row_count']}")
        print(f"Columns       : {profile['column_count']}")
        print(f"Commodities   : {profile['commodity_count']}")
        print(f"States        : {profile['state_count']}")
        print(f"Markets       : {profile['market_count']}")
        print(f"Duplicates    : {profile['duplicate_rows']}")
        print(f"Coverage      : {coverage['coverage_ratio']:.2%}")

        print("\n--- INGESTION COMPLETE ---")
        print(f"Normalized data saved to: {args.output}")

        return 0

    except Exception as exc:
        print("\nERROR during market ingestion:")
        print(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())