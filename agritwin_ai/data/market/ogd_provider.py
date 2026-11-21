from __future__ import annotations

import os
import time
from datetime import date
from typing import Any

import requests

from agritwin_ai.data.market.provider import MarketDataProvider


class OGDMarketDataProvider(MarketDataProvider):
    """
    Government of India OGD market-price provider.

    Dataset:
    Current Daily Price of Various Commodities from Various
    Markets (Mandi)

    Resource ID:
    9ef84268-d588-465a-a308-a864a43d0070

    Important API limitation:
    The underlying Elasticsearch index enforces:
        from + size <= 10000

    Therefore large datasets must be partitioned before pagination.
    State is used as the primary partition because the OGD API
    supports state filtering reliably.
    """

    name = "ogd"

    RESOURCE_ID = (
        "9ef84268-d588-465a-a308-a864a43d0070"
    )

    BASE_URL = (
        "https://api.data.gov.in/resource/"
    )

    DEFAULT_PAGE_SIZE = 1000

    # Current Indian states and union territories exposed by
    # agricultural market datasets. The API may omit states with
    # no records on a given day.
    STATES = (
        "Andhra Pradesh",
        "Arunachal Pradesh",
        "Assam",
        "Bihar",
        "Chhattisgarh",
        "Goa",
        "Gujarat",
        "Haryana",
        "Himachal Pradesh",
        "Jharkhand",
        "Karnataka",
        "Kerala",
        "Keralam",
        "Madhya Pradesh",
        "Maharashtra",
        "Manipur",
        "Meghalaya",
        "Mizoram",
        "Nagaland",
        "Odisha",
        "Punjab",
        "Rajasthan",
        "Sikkim",
        "Tamil Nadu",
        "Telangana",
        "Tripura",
        "Uttar Pradesh",
        "Uttarakhand",
        "West Bengal",
        "Andaman and Nicobar Islands",
        "Chandigarh",
        "Dadra and Nagar Haveli and Daman and Diu",
        "Delhi",
        "Jammu and Kashmir",
        "Ladakh",
        "Lakshadweep",
        "Puducherry",
    )

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> None:

        self.endpoint = (
            endpoint
            or f"{self.BASE_URL}{self.RESOURCE_ID}"
        )

        self.api_key = (
            api_key
            or os.getenv("DATA_GOV_API_KEY")
        )

        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if not self.endpoint:
            raise ValueError(
                "OGD API endpoint cannot be empty."
            )

    def _request(
        self,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        request_params = dict(params or {})

        request_params.update(
            {
                "api-key": self.api_key,
                "format": "json",
            }
        )

        last_error: Exception | None = None

        for attempt in range(
            1,
            self.max_retries + 1,
        ):
            try:
                response = requests.get(
                    self.endpoint,
                    params=request_params,
                    headers={
                        "User-Agent": "AgriTwin/1.0",
                        "Accept": "application/json",
                    },
                    timeout=self.timeout,
                )

                response.raise_for_status()

                payload = response.json()

                if not isinstance(payload, dict):
                    raise ValueError(
                        "OGD API response must be a JSON object."
                    )

                status = payload.get("status")

                if status not in {
                    None,
                    "ok",
                }:
                    raise RuntimeError(
                        "OGD API returned unexpected "
                        f"status: {status!r}"
                    )

                records = payload.get("records")

                if records is None:
                    raise ValueError(
                        "OGD response does not contain "
                        "a 'records' field."
                    )

                if not isinstance(records, list):
                    raise ValueError(
                        "OGD 'records' field must be a list."
                    )

                return payload

            except requests.RequestException as exc:
                last_error = exc

                if attempt >= self.max_retries:
                    break

                time.sleep(
                    self.retry_delay * attempt
                )

        raise RuntimeError(
            "OGD API request failed after "
            f"{self.max_retries} attempts."
        ) from last_error

    def fetch_latest(
        self,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:

        if limit <= 0:
            raise ValueError(
                "limit must be positive."
            )

        payload = self._request(
            {
                "offset": 0,
                "limit": limit,
            }
        )

        return payload["records"]

    def fetch_range(
        self,
        start_date: date,
        end_date: date,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:

        if end_date < start_date:
            raise ValueError(
                "end_date cannot be earlier "
                "than start_date."
            )

        if limit <= 0:
            raise ValueError(
                "limit must be positive."
            )

        payload = self._request(
            {
                "filters[arrival_date]": (
                    f"{start_date.strftime('%d/%m/%Y')}"
                    f"|"
                    f"{end_date.strftime('%d/%m/%Y')}"
                ),
                "offset": 0,
                "limit": limit,
            }
        )

        return payload["records"]

    def fetch_state(
        self,
        state: str,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_records: int | None = None,
    ) -> list[dict[str, Any]]:

        state = state.strip()

        if not state:
            raise ValueError(
                "state cannot be empty."
            )

        if page_size <= 0:
            raise ValueError(
                "page_size must be positive."
            )

        if max_records is not None and max_records <= 0:
            raise ValueError(
                "max_records must be positive."
            )

        records: list[dict[str, Any]] = []

        offset = 0
        total: int | None = None

        while True:

            payload = self._request(
                {
                    "filters[state.keyword]": state,
                    "offset": offset,
                    "limit": page_size,
                }
            )

            batch = payload["records"]

            if any(
                str(record.get("state", "")).strip() != state
                for record in batch
            ):
                raise RuntimeError(
                    f"OGD state partition validation failed for "
                    f"{state!r}. API returned records from another state."
                )

            if total is None:
                raw_total = payload.get("total")

                if raw_total is not None:
                    total = int(raw_total)

            if not batch:
                break

            records.extend(batch)

            if max_records is not None:
                if len(records) >= max_records:
                    records = records[:max_records]
                    break

            if total is not None and len(records) >= total:
                break

            if len(batch) < page_size:
                break

            offset += page_size

        return records


    def fetch_market_history(
        self,
        state: str,
        district: str,
        commodity: str,
        start_date: date,
        end_date: date,
        limit: int = 9000,
    ) -> list[dict[str, Any]]:
        """Fetch historical rows for one state/district/commodity partition.

        ``arrival_date`` is intentionally filtered client-side. OGD's generic
        ``filters[field]`` parameter is an equality filter, not a date-range
        operator; sending ``start|end`` would only match those two dates and
        silently destroy the historical training set. The bounded regional
        partition is paginated, then the caller filters dates after parsing.
        """
        if end_date < start_date:
            raise ValueError("end_date cannot be earlier than start_date.")
        if limit <= 0 or limit > 9000:
            raise ValueError("limit must be between 1 and 9000.")
        if not self.api_key:
            raise RuntimeError("DATA_GOV_API_KEY is not configured.")
        if not state.strip() or not district.strip() or not commodity.strip():
            raise ValueError("state, district and commodity are required.")

        page_size = min(1000, limit)
        offset = 0
        total: int | None = None
        records: list[dict[str, Any]] = []
        base_filters = {
            "filters[state.keyword]": state.strip(),
            "filters[district.keyword]": district.strip(),
            "filters[commodity.keyword]": commodity.strip(),
        }
        while offset < limit and offset < 10000:
            page_limit = min(page_size, limit - offset, 10000 - offset)
            payload = self._request({
                **base_filters,
                "offset": offset,
                "limit": page_limit,
            })
            batch = payload["records"]
            for record in batch:
                if str(record.get("state", "")).strip().casefold() != state.strip().casefold():
                    raise RuntimeError("OGD historical partition returned a different state.")
                if str(record.get("district", "")).strip().casefold() != district.strip().casefold():
                    raise RuntimeError("OGD historical partition returned a different district.")
                if str(record.get("commodity", "")).strip().casefold() != commodity.strip().casefold():
                    raise RuntimeError("OGD historical partition returned a different commodity.")
            if total is None and payload.get("total") is not None:
                total = int(payload["total"])
            if not batch:
                break
            records.extend(batch)
            offset += len(batch)
            if total is not None and offset >= total:
                break
            if len(batch) < page_limit:
                break

        # Only return records inside the requested history window. Parse the
        # two common AGMARKNET date formats without depending on pandas here.
        from datetime import datetime
        filtered: list[dict[str, Any]] = []
        for record in records:
            raw_date = record.get("arrival_date") or record.get("date")
            parsed = None
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    parsed = datetime.strptime(str(raw_date).strip(), fmt).date()
                    break
                except (TypeError, ValueError):
                    continue
            if parsed is not None and start_date <= parsed <= end_date:
                filtered.append(record)
        return filtered

    def fetch_all_partitioned(
        self,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_records: int | None = None,
    ) -> list[dict[str, Any]]:

        if page_size <= 0:
            raise ValueError(
                "page_size must be positive."
            )

        if max_records is not None and max_records <= 0:
            raise ValueError(
                "max_records must be positive."
            )

        all_records: list[dict[str, Any]] = []

        for index, state in enumerate(
            self.STATES,
            start=1,
        ):
            print(
                f"\n[{index}/{len(self.STATES)}] "
                f"Fetching {state}..."
            )

            try:
                state_records = self.fetch_state(
                    state=state,
                    page_size=page_size,
                )

            except RuntimeError as exc:
                print(
                    f"  WARNING: failed to fetch "
                    f"{state}: {exc}"
                )
                continue

            if not state_records:
                print(
                    f"  {state}: 0 records"
                )
                continue

            all_records.extend(state_records)

            print(
                f"  {state}: "
                f"{len(state_records)} records"
            )

            print(
                f"  Total collected: "
                f"{len(all_records)}"
            )

            if max_records is not None:
                if len(all_records) >= max_records:
                    all_records = all_records[
                        :max_records
                    ]
                    break

        return all_records

    def fetch_all(
        self,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_records: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch records using the provider's generic offset pagination.

        This method intentionally preserves the original provider contract
        used by unit tests and generic callers.

        For downloading the complete OGD dataset, use
        fetch_all_partitioned(), because the OGD Elasticsearch backend
        rejects requests where offset + limit exceeds 10000.
        """

        if page_size <= 0:
            raise ValueError(
                "page_size must be positive."
            )

        if max_records is not None and max_records <= 0:
            raise ValueError(
                "max_records must be positive."
            )

        all_records: list[dict[str, Any]] = []

        offset = 0
        total: int | None = None

        while True:

            payload = self._request(
                {
                    "offset": offset,
                    "limit": page_size,
                }
            )

            records = payload["records"]

            if total is None:
                raw_total = payload.get("total")

                if raw_total is not None:
                    total = int(raw_total)

            if not records:
                break

            all_records.extend(records)

            print(
                f"OGD ingestion: "
                f"{len(all_records)}"
                + (
                    f"/{total}"
                    if total is not None
                    else ""
                )
                + " records"
            )

            if max_records is not None:
                if len(all_records) >= max_records:
                    all_records = all_records[
                        :max_records
                    ]
                    break

            if (
                total is not None
                and len(all_records) >= total
            ):
                break

            if len(records) < page_size:
                break

            offset += page_size

        return all_records
    def health_check(self) -> bool:
        try:
            payload = self._request(
                {
                    "offset": 0,
                    "limit": 1,
                }
            )

            return isinstance(
                payload.get("records"),
                list,
            )

        except Exception:
            return False