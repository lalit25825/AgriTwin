from pathlib import Path

import pandas as pd

from agritwin_ai.tools.market.ingest_market import build_parser


def test_ingest_cli_requires_csv():
    parser = build_parser()

    try:
        parser.parse_args([])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError(
            "CLI should require --csv."
        )


def test_ingest_cli_accepts_csv():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--csv",
            "market.csv",
        ]
    )

    assert args.csv == "market.csv"


def test_ingest_cli_output_override():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--csv",
            "market.csv",
            "--output",
            "custom.csv",
        ]
    )

    assert args.output == "custom.csv"


def test_ingest_cli_no_raw():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--csv",
            "market.csv",
            "--no-raw",
        ]
    )

    assert args.no_raw is True