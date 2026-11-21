from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from agritwin_ai.data.market.historical_store import (
    MarketHistoricalStore,
)
from agritwin_ai.data.market.normalizer import (
    normalize_dataframe,
)


class MarketSnapshotManager:
    """
    Manage daily market snapshots and append them to the
    persistent historical market store.
    """

    def __init__(
        self,
        history_path: str | Path,
    ):
        self.history_path = Path(
            history_path
        )

        self.store = MarketHistoricalStore(
            self.history_path
        )

    def ingest_snapshot(
        self,
        dataframe: pd.DataFrame,
        source: str = "OGD/AGMARKNET",
    ) -> dict[str, int | str]:
        """
        Normalize and append one market snapshot.
        """

        if dataframe.empty:
            return {
                "snapshot_date": "",
                "incoming_rows": 0,
                "new_rows": 0,
                "duplicates_removed": 0,
                "final_rows": len(
                    self.store.load()
                ),
            }

        normalized = normalize_dataframe(
            dataframe,
            source=source,
        )

        snapshot_dates = (
            normalized["date"]
            .dropna()
            .unique()
            .tolist()
        )

        if not snapshot_dates:
            raise ValueError(
                "Snapshot contains no valid dates."
            )

        if len(snapshot_dates) > 1:
            raise ValueError(
                "A daily snapshot must contain "
                "exactly one date. Found: "
                f"{snapshot_dates}"
            )

        snapshot_date = str(
            snapshot_dates[0]
        )

        result = self.store.append(
            normalized
        )

        result["snapshot_date"] = (
            snapshot_date
        )

        return result

    def latest_snapshot_date(
        self,
    ) -> str | None:
        history = self.store.load()

        if history.empty:
            return None

        dates = pd.to_datetime(
            history["date"],
            errors="coerce",
        )

        if dates.dropna().empty:
            return None

        return dates.max().strftime(
            "%Y-%m-%d"
        )

    def snapshot_count(self) -> int:
        history = self.store.load()

        if history.empty:
            return 0

        return (
            history["date"]
            .dropna()
            .nunique()
        )