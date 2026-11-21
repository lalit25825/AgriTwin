from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from agritwin_ai.data.market.schema import MarketRecord


class MarketNormalizer:
    """
    Normalize market records from OGD/AGMARKNET and other supported
    market-data shapes into canonical MarketRecord objects.

    The public API is compatible with the existing MarketDataCollector
    and test suite.
    """

    FIELD_ALIASES = {
        "date": (
            "date",
            "arrival_date",
        ),
        "state": (
            "state",
            "state_name",
        ),
        "district": (
            "district",
            "district_name",
        ),
        "market": (
            "market",
            "market_name",
        ),
        "commodity": (
            "commodity",
            "commodity_name",
        ),
        "variety": (
            "variety",
            "variety_name",
        ),
        "grade": (
            "grade",
            "grade_name",
        ),
        "arrival_quantity": (
            "arrival_quantity",
            "arrival",
        ),
        "min_price": (
            "min_price",
            "minimum_price",
        ),
        "max_price": (
            "max_price",
            "maximum_price",
        ),
        "modal_price": (
            "modal_price",
            "modal",
        ),
    }

    def normalize(
        self,
        record: dict[str, Any] | None = None,
        source: str | None = None,
        raw_record: dict[str, Any] | None = None,
    ) -> MarketRecord:
        """
        Normalize one raw market-data record into MarketRecord.
        """
        if record is None:
            record = raw_record

        if record is None:
            raise ValueError(
                "A market record is required."
            )

        parsed_date = self._parse_date(
            self._get(record, "date")
        )

        state = self._required_text(
            self._get(record, "state"),
            "state",
        )

        district = self._optional_text(
            self._get(record, "district")
        )

        market = self._required_text(
            self._get(record, "market"),
            "market",
        )

        commodity = self._required_text(
            self._get(record, "commodity"),
            "commodity",
        )

        variety = self._optional_text(
            self._get(record, "variety")
        )

        grade = self._optional_text(
            self._get(record, "grade")
        )

        arrival_quantity = self._parse_optional_number(
            self._get(record, "arrival_quantity"),
            "arrival_quantity",
        )

        min_price = self._parse_required_number(
            self._get(record, "min_price"),
            "min_price",
        )

        max_price = self._parse_required_number(
            self._get(record, "max_price"),
            "max_price",
        )

        modal_price = self._parse_required_number(
            self._get(record, "modal_price"),
            "modal_price",
        )

        normalized_source = (
            source
            if source is not None
            else record.get(
                "source",
                "OGD/AGMARKNET",
            )
        )

        normalized_source = str(
            normalized_source
        ).strip()

        if not normalized_source:
            raise ValueError(
                "source cannot be empty."
            )

        return MarketRecord(
            date=parsed_date,
            state=state,
            district=district,
            market=market,
            commodity=commodity,
            variety=variety,
            grade=grade,
            arrival_quantity=arrival_quantity,
            min_price=min_price,
            max_price=max_price,
            modal_price=modal_price,
            source=normalized_source,
            collected_at=self._parse_collected_at(
                record.get("collected_at")
            ),
        )

    def normalize_many(
        self,
        records: list[dict[str, Any]],
        source: str | None = None,
    ) -> list[MarketRecord]:
        """
        Normalize multiple records.
        """

        return [
            self.normalize(
                record,
                source=source,
            )
            for record in records
        ]

    def _get(
        self,
        record: dict[str, Any],
        field: str,
    ) -> Any:
        """
        Return the first available alias for a canonical field.
        """

        for alias in self.FIELD_ALIASES[field]:
            if alias in record:
                return record[alias]

        return None

    @staticmethod
    def _required_text(
        value: Any,
        field_name: str,
    ) -> str:
        if value is None:
            raise ValueError(
                f"{field_name} is required."
            )

        if pd.isna(value):
            raise ValueError(
                f"{field_name} is required."
            )

        value = str(value).strip()

        if not value:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return value

    @staticmethod
    def _optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        if pd.isna(value):
            return None

        value = str(value).strip()

        return value or None

    @staticmethod
    def _parse_required_number(
        value: Any,
        field_name: str,
    ) -> float:
        if value is None:
            raise ValueError(
                f"{field_name} is required."
            )

        if isinstance(value, str):
            value = value.strip().replace(",", "")

        try:
            parsed = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid numeric value for {field_name}: "
                f"{value!r}"
            ) from None

        if pd.isna(parsed):
            raise ValueError(
                f"Invalid numeric value for {field_name}: "
                f"{value!r}"
            )

        return parsed

    @staticmethod
    def _parse_optional_number(
        value: Any,
        field_name: str,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return None

            value = value.replace(",", "")

        try:
            parsed = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid numeric value for {field_name}: "
                f"{value!r}"
            ) from None

        if pd.isna(parsed):
            return None

        return parsed

    @staticmethod
    def _parse_date(
        value: Any,
    ):
        if value is None:
            raise ValueError(
                "date is required."
            )

        if isinstance(value, str):
            value = value.strip()

            if not value:
                raise ValueError(
                    "date cannot be empty."
                )

            # ISO format: YYYY-MM-DD
            # Must be parsed without day-first semantics.
            if (
                len(value) == 10
                and value[4] == "-"
                and value[7] == "-"
            ):
                parsed = pd.to_datetime(
                    value,
                    format="%Y-%m-%d",
                    errors="coerce",
                )
            else:
                # OGD/AGMARKNET format: DD/MM/YYYY
                parsed = pd.to_datetime(
                    value,
                    dayfirst=True,
                    errors="coerce",
                )
        else:
            parsed = pd.to_datetime(
                value,
                errors="coerce",
            )

        if pd.isna(parsed):
            raise ValueError(
                f"Invalid date value: {value!r}"
            )

        return parsed.date()
    
        if value is None:
            raise ValueError(
                "date is required."
            )

        if isinstance(value, str):
            value = value.strip()

        parsed = pd.to_datetime(
            value,
            dayfirst=True,
            errors="coerce",
        )

        if pd.isna(parsed):
            raise ValueError(
                f"Invalid date value: {value!r}"
            )

        return parsed.date()

    @staticmethod
    def _parse_collected_at(
        value: Any,
    ) -> datetime:
        if value is None:
            return datetime.now(UTC)

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(
                    tzinfo=UTC
                )

            return value

        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(parsed):
            return datetime.now(UTC)

        result = parsed.to_pydatetime()

        if result.tzinfo is None:
            result = result.replace(
                tzinfo=UTC
            )

        return result


def normalize_record(
    record: dict[str, Any],
    source: str | None = None,
) -> MarketRecord:
    return MarketNormalizer().normalize(
        record,
        source=source,
    )


def normalize_dataframe(
    df: pd.DataFrame,
    source: str | None = None,
) -> pd.DataFrame:
    """
    Normalize a dataframe into canonical MarketRecord records.
    """

    normalizer = MarketNormalizer()

    records: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        market_record = normalizer.normalize(
            row.to_dict(),
            source=source,
        )

        records.append(
            market_record.model_dump()
        )

    normalized = pd.DataFrame(records)

    if normalized.empty:
        return normalized

    normalized["date"] = pd.to_datetime(
        normalized["date"],
        errors="raise",
    ).dt.strftime("%Y-%m-%d")

    normalized = normalized.sort_values(
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
    ).reset_index(drop=True)

    return normalized


def normalize_csv(
    input_path: str | Path,
    output_path: str | Path,
    source: str | None = None,
) -> pd.DataFrame:
    """
    Normalize an OGD CSV and save canonical records.
    """

    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input market file does not exist: "
            f"{input_path}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(input_path)

    normalized = normalize_dataframe(
        df,
        source=source,
    )

    normalized.to_csv(
        output_path,
        index=False,
    )

    return normalized