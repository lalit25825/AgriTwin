from pathlib import Path

import pandas as pd

from agritwin_ai.data.market.snapshot import (
    MarketSnapshotManager,
)


def make_snapshot(
    date: str = "2026-09-09",
):
    return pd.DataFrame(
        [
            {
                "arrival_date": date,
                "state": "Maharashtra",
                "district": "Nashik",
                "market": "Lasalgaon",
                "commodity": "Onion",
                "variety": "Onion",
                "grade": "FAQ",
                "min_price": 1800,
                "max_price": 2400,
                "modal_price": 2200,
            }
        ]
    )


def test_snapshot_manager_appends_new_snapshot(
    tmp_path: Path,
):
    history_path = (
        tmp_path / "market_history.csv"
    )

    manager = MarketSnapshotManager(
        history_path
    )

    first = manager.ingest_snapshot(
        make_snapshot("2026-09-09")
    )

    assert first["incoming_rows"] == 1
    assert first["new_rows"] == 1
    assert first["final_rows"] == 1

    second = manager.ingest_snapshot(
        make_snapshot("2026-09-10")
    )

    assert second["incoming_rows"] == 1
    assert second["new_rows"] == 1
    assert second["final_rows"] == 2

    assert (
        manager.snapshot_count()
        == 2
    )


def test_snapshot_manager_deduplicates_same_day(
    tmp_path: Path,
):
    history_path = (
        tmp_path / "market_history.csv"
    )

    manager = MarketSnapshotManager(
        history_path
    )

    manager.ingest_snapshot(
        make_snapshot("2026-09-09")
    )

    result = manager.ingest_snapshot(
        make_snapshot("2026-09-09")
    )

    assert result["incoming_rows"] == 1
    assert result["new_rows"] == 0
    assert result["final_rows"] == 1


def test_snapshot_manager_reports_latest_date(
    tmp_path: Path,
):
    history_path = (
        tmp_path / "market_history.csv"
    )

    manager = MarketSnapshotManager(
        history_path
    )

    assert (
        manager.latest_snapshot_date()
        is None
    )

    manager.ingest_snapshot(
        make_snapshot("2026-09-09")
    )

    assert (
        manager.latest_snapshot_date()
        == "2026-09-09"
    )


def test_snapshot_manager_rejects_multiple_dates(
    tmp_path: Path,
):
    history_path = (
        tmp_path / "market_history.csv"
    )

    manager = MarketSnapshotManager(
        history_path
    )

    dataframe = pd.concat(
        [
            make_snapshot("2026-09-09"),
            make_snapshot("2026-09-10"),
        ],
        ignore_index=True,
    )

    try:
        manager.ingest_snapshot(
            dataframe
        )
        assert False, (
            "Expected ValueError"
        )
    except ValueError as exc:
        assert (
            "exactly one date"
            in str(exc)
        )