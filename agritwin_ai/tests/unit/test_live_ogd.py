from agritwin_ai.data.market.ogd_provider import (
    OGDMarketDataProvider,
)


def main():
    provider = OGDMarketDataProvider()

    print("=" * 70)
    print("AgriTwin OGD LIVE API TEST")
    print("=" * 70)

    print("\nEndpoint:")
    print(provider.endpoint)

    print("\nFetching 5 records...\n")

    records = provider.fetch_latest(
        limit=5
    )

    print(f"Records received: {len(records)}")

    for index, record in enumerate(
        records,
        start=1,
    ):
        print(f"\nRecord {index}")
        print("-" * 40)

        for key, value in record.items():
            print(
                f"{key:15}: {value}"
            )

    print("\n" + "=" * 70)
    print("LIVE API TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()