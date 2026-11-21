from __future__ import annotations

from pathlib import Path

import pandas as pd


HISTORY_COLUMNS = [
    "date",
    "state",
    "district",
    "market",
    "commodity",
    "variety",
    "grade",
    "arrival_quantity",
    "min_price",
    "max_price",
    "modal_price",
    "source",
    "collected_at",
]


DEDUP_COLUMNS = [
    "date",
    "state",
    "district",
    "market",
    "commodity",
    "variety",
    "grade",
]


class MarketHistoricalStore:
    """
    Persistent historical store for canonical market observations.

    The store is append-and-deduplicate:
        new daily snapshot
                 ↓
        historical CSV
                 ↓
        deduplicate by market/date identity
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(
                columns=HISTORY_COLUMNS
            )

        df = pd.read_csv(self.path)

        for column in HISTORY_COLUMNS:
            if column not in df.columns:
                df[column] = None

        return df[HISTORY_COLUMNS]

    def append(
        self,
        records: pd.DataFrame,
    ) -> dict[str, int]:
        if records.empty:
            return {
                "previous_rows": len(self.load()),
                "incoming_rows": 0,
                "duplicates_removed": 0,
                "final_rows": len(self.load()),
                "new_rows": 0,
            }

        incoming = records.copy()

        for column in HISTORY_COLUMNS:
            if column not in incoming.columns:
                incoming[column] = None

        incoming = incoming[HISTORY_COLUMNS]

        existing = self.load()

        previous_rows = len(existing)
        incoming_rows = len(incoming)

        combined = (
            incoming.copy()
            if existing.empty
            else pd.concat([existing, incoming], ignore_index=True)
        )

        combined = combined.drop_duplicates(
            subset=DEDUP_COLUMNS,
            keep="last",
        )

        duplicates_removed = (
            previous_rows
            + incoming_rows
            - len(combined)
        )

        combined["date"] = pd.to_datetime(
            combined["date"],
            errors="coerce",
        )

        combined = combined.sort_values(
            [
                "date",
                "state",
                "district",
                "market",
                "commodity",
                "variety",
                "grade",
            ],
            na_position="last",
        )

        combined["date"] = combined["date"].dt.strftime(
            "%Y-%m-%d"
        )

        combined.to_csv(
            self.path,
            index=False,
        )

        return {
            "previous_rows": previous_rows,
            "incoming_rows": incoming_rows,
            "duplicates_removed": duplicates_removed,
            "final_rows": len(combined),
            "new_rows": len(combined) - previous_rows,
        }