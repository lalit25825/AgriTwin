from __future__ import annotations

import os
import re
import threading
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from agritwin_ai.data.market.historical_store import MarketHistoricalStore
from agritwin_ai.data.market.normalizer import MarketNormalizer
from agritwin_ai.data.market.ogd_provider import OGDMarketDataProvider
from agritwin_ai.models.market.forecast_service import MarketForecastService


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


class MarketIntelligenceService:
    """Regional mandi intelligence backed by OGD/AGMARKNET and local history.

    Facts are always taken from a market-data source. Forecasts are calculated
    separately and labelled with their training depth and validation quality.
    This service deliberately does not manufacture trade ticks: the official
    public OGD price dataset is daily, not an exchange-style streaming feed.
    """

    SOURCE_NAME = "Government of India OGD / AGMARKNET"
    SOURCE_URL = "https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi"
    ENAM_URL = "https://enam.gov.in/dashboard"
    ENAM_TRADING_URL = "https://www.enam.gov.in/web/trading-details"
    MSAMB_URL = "https://www.msamb.com/ApmcDetail/APMCPriceInformation"

    STATE_ALIASES = {
        "maharashtra": "Maharashtra", "mh": "Maharashtra",
        "gujarat": "Gujarat", "gj": "Gujarat",
        "madhya pradesh": "Madhya Pradesh", "mp": "Madhya Pradesh",
        "karnataka": "Karnataka", "ka": "Karnataka",
        "telangana": "Telangana", "ts": "Telangana",
        "andhra pradesh": "Andhra Pradesh", "ap": "Andhra Pradesh",
        "rajasthan": "Rajasthan", "rj": "Rajasthan",
        "uttar pradesh": "Uttar Pradesh", "up": "Uttar Pradesh",
        "punjab": "Punjab", "pb": "Punjab",
        "haryana": "Haryana", "hr": "Haryana",
        "tamil nadu": "Tamil Nadu", "tn": "Tamil Nadu",
    }

    CITY_TO_DISTRICT = {
        "nashik": ("Nashik", "Maharashtra"),
        "nasik": ("Nashik", "Maharashtra"),
        "lasalgaon": ("Nashik", "Maharashtra"),
        "lasangaon": ("Nashik", "Maharashtra"),
        "pimpalgaon baswant": ("Nashik", "Maharashtra"),
        "niphad": ("Nashik", "Maharashtra"),
        "sinnar": ("Nashik", "Maharashtra"),
        "yeola": ("Nashik", "Maharashtra"),
        "manmad": ("Nashik", "Maharashtra"),
        "malegaon": ("Nashik", "Maharashtra"),
        "dhule": ("Dhule", "Maharashtra"),
        "jalgaon": ("Jalgaon", "Maharashtra"),
        "ahmednagar": ("Ahilyanagar", "Maharashtra"),
        "ahilyanagar": ("Ahilyanagar", "Maharashtra"),
        "chhatrapati sambhajinagar": ("Chhatrapati Sambhajinagar", "Maharashtra"),
        "aurangabad": ("Chhatrapati Sambhajinagar", "Maharashtra"),
        "pune": ("Pune", "Maharashtra"),
        "mumbai": ("Mumbai", "Maharashtra"),
        "thane": ("Thane", "Maharashtra"),
        "palghar": ("Palghar", "Maharashtra"),
        "nagpur": ("Nagpur", "Maharashtra"),
        "akola": ("Akola", "Maharashtra"),
        "sangli": ("Sangli", "Maharashtra"),
        "kolhapur": ("Kolhapur", "Maharashtra"),
        "solapur": ("Solapur", "Maharashtra"),
        "indore": ("Indore", "Madhya Pradesh"),
        "ujjain": ("Ujjain", "Madhya Pradesh"),
        "vadodara": ("Vadodara", "Gujarat"),
        "rajkot": ("Rajkot", "Gujarat"),
        "surat": ("Surat", "Gujarat"),
        "jaipur": ("Jaipur", "Rajasthan"),
        "kota": ("Kota", "Rajasthan"),
    }

    # Ordered first-ring fallback. The public feed contains district/mandi
    # names but not consistently machine-readable mandi coordinates.
    DISTRICT_NEIGHBOURS = {
        "nashik": ["Dhule", "Jalgaon", "Chhatrapati Sambhajinagar", "Ahilyanagar", "Thane", "Palghar", "Nandurbar"],
        "dhule": ["Nashik", "Nandurbar", "Jalgaon"],
        "jalgaon": ["Nashik", "Dhule", "Nandurbar", "Buldhana", "Chhatrapati Sambhajinagar"],
        "ahilyanagar": ["Nashik", "Pune", "Beed", "Chhatrapati Sambhajinagar", "Solapur"],
        "pune": ["Ahilyanagar", "Nashik", "Satara", "Solapur", "Raigad", "Thane"],
        "thane": ["Palghar", "Nashik", "Pune", "Raigad"],
        "palghar": ["Thane", "Nashik", "Nandurbar"],
        "nagpur": ["Wardha", "Bhandara", "Amravati", "Chandrapur"],
        "akola": ["Amravati", "Buldhana", "Washim", "Yavatmal"],
        "sangli": ["Kolhapur", "Satara", "Solapur"],
        "kolhapur": ["Sangli", "Satara", "Belagavi"],
        "solapur": ["Pune", "Ahilyanagar", "Sangli", "Osmanabad", "Beed"],
    }

    COMMODITY_ALIASES = {
        "onions": "onion", "potatoes": "potato", "tomatoes": "tomato",
        "green chilli": "green chilli", "chillies": "chilli",
        "soyabean": "soybean", "soya bean": "soybean",
    }

    REQUIRED_COLUMNS = [
        "date", "state", "district", "market", "commodity",
        "variety", "grade", "arrival_quantity", "min_price",
        "max_price", "modal_price", "source", "collected_at",
    ]

    def __init__(
        self,
        data_path: str | Path | None = None,
        history_path: str | Path | None = None,
        provider: Any | None = None,
        cache_ttl_seconds: int | None = None,
        backfill_days: int | None = None,
    ) -> None:
        root = PROJECT_ROOT
        self.data_path = Path(data_path) if data_path else root / "data/market/processed/market_records.csv"
        self.history_path = Path(history_path) if history_path else self.data_path.parent / "market_live_history.csv"
        self.history_store = MarketHistoricalStore(self.history_path)
        self.provider = provider or OGDMarketDataProvider(timeout=25, max_retries=2, retry_delay=1.0)
        self.normalizer = MarketNormalizer()
        self.cache_ttl_seconds = int(cache_ttl_seconds or os.getenv("MARKET_CACHE_TTL_SECONDS", "300"))
        self.backfill_days = int(backfill_days if backfill_days is not None else os.getenv("MARKET_HISTORY_BACKFILL_DAYS", "365"))
        self._state_cache: dict[str, tuple[datetime, pd.DataFrame, str | None]] = {}
        self._backfill_cache: dict[tuple[str, str, str], tuple[datetime, pd.DataFrame, str | None]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _key(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())

    @classmethod
    def _canonical_commodity(cls, value: str) -> str:
        key = str(value or "").strip().casefold()
        return cls.COMMODITY_ALIASES.get(key, key)

    def _api_configured(self) -> bool:
        return bool(os.getenv("DATA_GOV_API_KEY") or getattr(self.provider, "api_key", None))

    def _load_local(self) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for path in (self.data_path, self.history_path):
            if not path.exists():
                continue
            try:
                frame = pd.read_csv(path, low_memory=False)
                if not frame.empty:
                    frames.append(frame)
            except (OSError, pd.errors.ParserError, UnicodeDecodeError):
                continue
        if not frames:
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        frame = pd.concat(frames, ignore_index=True, sort=False)
        for col in self.REQUIRED_COLUMNS:
            if col not in frame.columns:
                frame[col] = None
        return self._clean_frame(frame)

    def _clean_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        result = frame.copy()
        for col in self.REQUIRED_COLUMNS:
            if col not in result.columns:
                result[col] = None
        raw_dates = result["date"].astype(str).str.strip()
        iso_mask = raw_dates.str.match(r"^\d{4}-\d{1,2}-\d{1,2}(?:$|T| )")
        parsed_dates = pd.Series(pd.NaT, index=result.index, dtype="datetime64[ns]")
        if iso_mask.any():
            parsed_dates.loc[iso_mask] = pd.to_datetime(raw_dates.loc[iso_mask], errors="coerce", dayfirst=False)
        if (~iso_mask).any():
            parsed_dates.loc[~iso_mask] = pd.to_datetime(raw_dates.loc[~iso_mask], errors="coerce", dayfirst=True)
        result["date"] = parsed_dates
        for col in ("min_price", "max_price", "modal_price", "arrival_quantity"):
            result[col] = pd.to_numeric(result[col], errors="coerce")
        result["commodity"] = result["commodity"].astype(str).str.strip()
        result["market"] = result["market"].astype(str).str.strip()
        result["district"] = result["district"].fillna("").astype(str).str.strip()
        result["state"] = result["state"].fillna("").astype(str).str.strip()
        result = result.dropna(subset=["date", "modal_price"])
        result = result[(result["modal_price"] > 0) & (result["market"] != "") & (result["commodity"] != "")]
        return result

    def _resolve_region(self, region: str, local: pd.DataFrame) -> tuple[str | None, str | None]:
        raw = str(region or "").strip()
        if not raw:
            return None, None
        key = raw.casefold().strip()
        key = re.sub(r"\s+(district|dist\.?|division)$", "", key).strip()
        parts = [re.sub(r"\s+(district|dist\.?|division)$", "", part.strip(), flags=re.I).strip() for part in raw.split(",") if part.strip()]
        explicit_state = None
        for part in reversed(parts):
            state = self.STATE_ALIASES.get(part.casefold())
            if state:
                explicit_state = state
                break
        if key in self.STATE_ALIASES:
            return self.STATE_ALIASES[key], None
        if key in self.CITY_TO_DISTRICT:
            district, mapped_state = self.CITY_TO_DISTRICT[key]
            return explicit_state or mapped_state, district
        for city, (district, mapped_state) in self.CITY_TO_DISTRICT.items():
            if city in key:
                return explicit_state or mapped_state, district
        for part in parts:
            if part.casefold() in self.STATE_ALIASES:
                continue
            exact = local[local["district"].str.casefold() == part.casefold()] if not local.empty else pd.DataFrame()
            if not exact.empty:
                return explicit_state or str(exact.iloc[0]["state"]), str(exact.iloc[0]["district"])
            market_match = local[local["market"].str.casefold().str.contains(re.escape(part.casefold()), na=False)] if not local.empty else pd.DataFrame()
            if not market_match.empty:
                return explicit_state or str(market_match.iloc[0]["state"]), str(market_match.iloc[0]["district"] or "")
        if explicit_state:
            return explicit_state, None
        return None, raw

    def _refresh_state(self, state: str, force: bool = False) -> tuple[pd.DataFrame, str | None]:
        now = datetime.now(timezone.utc)
        with self._lock:
            cached = self._state_cache.get(state.casefold())
            if cached and not force and (now - cached[0]).total_seconds() < self.cache_ttl_seconds:
                return cached[1].copy(), cached[2]
        if not self._api_configured():
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS), "DATA_GOV_API_KEY is not configured; using the local snapshot only."
        try:
            records = self.provider.fetch_state(state=state, page_size=1000, max_records=9000)
            normalized = self._normalize_records(records, "data.gov.in / AGMARKNET API")
            live_frame = self._clean_frame(pd.DataFrame(normalized)) if normalized else pd.DataFrame(columns=self.REQUIRED_COLUMNS)
            if not live_frame.empty:
                self.history_store.append(live_frame)
            with self._lock:
                self._state_cache[state.casefold()] = (now, live_frame.copy(), None)
            return live_frame, None
        except Exception as exc:  # upstream outages must not erase cached values
            message = f"Live OGD fetch failed: {type(exc).__name__}: {exc}"
            local = self._load_local()
            if not local.empty:
                local_state = local[local["state"].str.casefold() == state.casefold()]
                return local_state, message + "; showing saved observations instead."
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS), message

    def _normalize_records(self, records: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for record in records:
            try:
                item = self.normalizer.normalize(record=record, source=source)
                normalized.append(item.model_dump(mode="json"))
            except Exception:
                # A malformed row is skipped, never silently coerced into a price.
                continue
        return normalized

    def _backfill_market_history(self, state: str, district: str, commodity: str, force: bool = False) -> tuple[pd.DataFrame, str | None]:
        empty = pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        if self.backfill_days <= 0 or not self._api_configured():
            return empty, None
        cache_key = (state.casefold(), district.casefold(), commodity.casefold())
        now = datetime.now(timezone.utc)
        with self._lock:
            cached = self._backfill_cache.get(cache_key)
            if cached and not force:
                checked_at, cached_frame, cached_warning = cached
                ttl = 900 if cached_warning else 86400
                if (now - checked_at).total_seconds() < ttl:
                    return cached_frame.copy(), cached_warning
        fetcher = getattr(self.provider, "fetch_market_history", None)
        if not callable(fetcher):
            warning = "Provider does not expose historical backfill."
            with self._lock:
                self._backfill_cache[cache_key] = (now, empty.copy(), warning)
            return empty, warning
        try:
            end = datetime.now(ZoneInfo("Asia/Kolkata")).date()
            start = end - timedelta(days=self.backfill_days)
            records = fetcher(
                state=state,
                district=district,
                commodity=commodity,
                start_date=start,
                end_date=end,
                limit=9000,
            )
            normalized = self._normalize_records(records, "data.gov.in / AGMARKNET historical API")
            frame = self._clean_frame(pd.DataFrame(normalized)) if normalized else empty.copy()
            if not frame.empty:
                # Recheck dates locally; providers and upstream query filters can
                # differ in how they interpret date operators.
                frame = frame[(frame["date"].dt.date >= start) & (frame["date"].dt.date <= end)]
                frame = frame[
                    (frame["state"].str.casefold() == state.casefold())
                    & (frame["district"].str.casefold() == district.casefold())
                    & (frame["commodity"].str.casefold().map(self._canonical_commodity) == self._canonical_commodity(commodity))
                ]
            if not frame.empty:
                self.history_store.append(frame)
            with self._lock:
                self._backfill_cache[cache_key] = (now, frame.copy(), None)
            return frame, None
        except Exception as exc:
            warning = f"Historical backfill unavailable: {type(exc).__name__}: {exc}"
            with self._lock:
                self._backfill_cache[cache_key] = (now, empty.copy(), warning)
            return empty, warning

    def _get_dataset(self, region: str, commodity: str, force_refresh: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
        local = self._load_local()
        state, district = self._resolve_region(region, local)
        live = pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        warning: str | None = None
        live_warning: str | None = None
        if state:
            live, live_warning = self._refresh_state(state, force=force_refresh)
            warning = live_warning
        frames = [frame for frame in (local, live) if not frame.empty]
        combined = self._clean_frame(pd.concat(frames, ignore_index=True, sort=False)) if frames else pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        if state and not combined.empty:
            state_rows = combined[combined["state"].str.casefold() == state.casefold()].copy()
            if not state_rows.empty:
                combined = state_rows
            else:
                # Legacy/manual CSV rows may omit state and district entirely.
                # Preserve such rows only when the user's request names an
                # exact mandi/district; never widen to unrelated labelled rows.
                unlabelled = combined[combined["state"].fillna("").astype(str).str.strip() == ""].copy()
                region_key = self._key(region)
                district_mask = unlabelled["district"].astype(str).str.casefold() == str(district or "").casefold()
                market_keys = unlabelled["market"].astype(str).map(self._key)
                market_mask = (market_keys == region_key) | market_keys.str.contains(re.escape(region_key), na=False)
                unlabelled_match = unlabelled[district_mask | market_mask].copy()
                combined = unlabelled_match

        canonical = self._canonical_commodity(commodity)
        if not combined.empty:
            names = combined["commodity"].str.casefold().str.strip()
            exact = names.map(self._canonical_commodity) == canonical
            if exact.any():
                combined = combined[exact].copy()
            else:
                contains = names.str.contains(re.escape(canonical), na=False)
                combined = combined[contains].copy()

        # Backfill the district that will actually drive the market decision.
        # When the requested district has no fresh quote for this crop, prefer
        # the best fresh first-ring neighbour; otherwise retain the local
        # district history. This avoids forecasting a dead local series while
        # recommending a different nearby mandi.
        history_warning: str | None = None
        backfill = pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        if state and district:
            backfill_district = district
            if not combined.empty:
                today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
                local_quotes = combined[combined["district"].str.casefold() == district.casefold()].copy()
                local_fresh = local_quotes[local_quotes["date"].dt.date.map(lambda d: (today - d).days <= 3)] if not local_quotes.empty else local_quotes
                if local_fresh.empty:
                    nearby_names = self.DISTRICT_NEIGHBOURS.get(district.casefold(), [])
                    nearby_quotes = combined[combined["district"].str.casefold().isin([name.casefold() for name in nearby_names])].copy()
                    if not nearby_quotes.empty:
                        nearby_quotes["_quote_age"] = nearby_quotes["date"].dt.date.map(lambda d: (today - d).days)
                        fresh_nearby = nearby_quotes[nearby_quotes["_quote_age"] <= 3]
                        candidates = fresh_nearby if not fresh_nearby.empty else nearby_quotes
                        latest_per_market = candidates.sort_values(["date", "modal_price"], ascending=[False, False]).drop_duplicates(["district", "market"])
                        if not latest_per_market.empty:
                            backfill_district = str(latest_per_market.sort_values(["_quote_age", "modal_price"], ascending=[True, False]).iloc[0]["district"])
            crop_label = commodity
            if not combined.empty:
                matching_names = combined.loc[
                    combined["commodity"].astype(str).str.casefold().map(self._canonical_commodity) == canonical,
                    "commodity",
                ].dropna().astype(str).str.strip()
                if not matching_names.empty:
                    crop_label = str(matching_names.mode().iloc[0])
                elif commodity.strip():
                    crop_label = commodity.strip().title()
            backfill, history_warning = self._backfill_market_history(
                state, backfill_district, crop_label, force=force_refresh
            )
            if not backfill.empty:
                combined = self._clean_frame(
                    backfill.copy() if combined.empty
                    else pd.concat([combined, backfill], ignore_index=True, sort=False)
                )
        if history_warning and not warning:
            warning = history_warning

        if not combined.empty:
            combined = combined.drop_duplicates(
                subset=["date", "state", "district", "market", "commodity", "variety", "grade", "modal_price"],
                keep="last",
            )

        # A successful Maharashtra download is not enough to claim that the
        # requested onion quote was fetched. The live dataset must contain the
        # requested commodity before it is labelled as a live quote source.
        live_matches = pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        if not live.empty:
            live_matches = live.copy()
            live_names = live_matches["commodity"].astype(str).str.casefold().str.strip()
            live_matches = live_matches[live_names.map(self._canonical_commodity) == canonical]
            if district and not live_matches.empty:
                local_live = live_matches[live_matches["district"].str.casefold() == district.casefold()]
                nearby_names = self.DISTRICT_NEIGHBOURS.get(district.casefold(), [])
                nearby_live = live_matches[live_matches["district"].str.casefold().isin([name.casefold() for name in nearby_names])]
                live_matches = pd.concat([local_live, nearby_live], ignore_index=True)
        live_snapshot_ok = not live_matches.empty and live_warning is None
        history_snapshot_ok = not backfill.empty and history_warning is None
        if live_snapshot_ok:
            source_status = "live_api"
            source_label = self.SOURCE_NAME
        elif history_snapshot_ok:
            source_status = "historical_api"
            source_label = "Government of India OGD / AGMARKNET historical records"
            if not warning:
                warning = "Historical API records were found, but no current daily quote was returned for this crop and region."
        else:
            source_status = "offline_cache" if not combined.empty else "unavailable"
            source_label = "Saved OGD / AGMARKNET observations"
        fetched_at = datetime.now(timezone.utc).isoformat()
        if state:
            with self._lock:
                cache_entry = self._state_cache.get(state.casefold())
            if cache_entry:
                fetched_at = cache_entry[0].isoformat()
        meta = {
            "state": state,
            "district": district,
            "source_status": source_status,
            "source": source_label,
            "fetched_at": fetched_at,
            "warning": warning,
            "api_configured": self._api_configured(),
        }
        return combined, meta

    def _regional_slice(self, frame: pd.DataFrame, state: str | None, district: str | None, region: str) -> tuple[pd.DataFrame, str, list[str]]:
        if frame.empty:
            return frame, "no_data", []
        if state:
            in_state = frame[frame["state"].str.casefold() == state.casefold()].copy()
        else:
            in_state = frame.copy()
        if district:
            # A named mandi such as Lasalgaon resolves to its parent district
            # for neighbour discovery, but the exact mandi request must remain
            # scoped to that mandi rather than every market in the district.
            region_key = re.sub(r"[^a-z0-9]+", "", str(region).casefold())
            district_key = re.sub(r"[^a-z0-9]+", "", district.casefold())
            if region_key and region_key != district_key and "," not in str(region):
                market_keys = in_state["market"].astype(str).str.casefold().str.replace(r"[^a-z0-9]+", "", regex=True)
                exact_market = in_state[market_keys == region_key].copy()
                if exact_market.empty:
                    exact_market = in_state[market_keys.str.contains(re.escape(region_key), na=False)].copy()
                if not exact_market.empty:
                    return exact_market, "requested_market", []
            local = in_state[in_state["district"].str.casefold() == district.casefold()].copy()
            neighbour_names = self.DISTRICT_NEIGHBOURS.get(district.casefold(), [])
            # Use the requested district when it has a recent published quote.
            # If its only prices are stale, include fresh neighbouring quotes
            # too so the user can compare rather than being trapped by old data.
            today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
            local_fresh = local[local["date"].dt.date.map(lambda d: (today - d).days <= 3)] if not local.empty else local
            if not local.empty and not local_fresh.empty:
                return local, "requested_district", []
            nearby_frames = []
            found_neighbours = []
            for neighbour in neighbour_names:
                nearby = in_state[in_state["district"].str.casefold() == neighbour.casefold()].copy()
                if not nearby.empty:
                    nearby_fresh = nearby[nearby["date"].dt.date.map(lambda d: (today - d).days <= 3)]
                    if not local.empty and not nearby_fresh.empty:
                        nearby = nearby_fresh
                    nearby_frames.append(nearby)
                    found_neighbours.append(neighbour)
            if nearby_frames:
                combined_nearby = pd.concat(nearby_frames, ignore_index=True)
                if not local.empty:
                    combined_nearby = pd.concat([local, combined_nearby], ignore_index=True)
                return combined_nearby, "nearby_districts", found_neighbours
            if not local.empty:
                return local, "requested_district", []
        elif state:
            return in_state, "state_wide", []
        else:
            direct = in_state[in_state["district"].str.casefold() == str(region).casefold()].copy()
            if not direct.empty:
                return direct, "requested_district", []
            direct = in_state[in_state["market"].str.casefold().str.contains(re.escape(str(region).casefold()), na=False)].copy()
            if not direct.empty:
                return direct, "requested_market", []
        # An unrecognised city/district must not silently receive prices from
        # unrelated parts of India. Return no data instead of a nationwide mix.
        if district and not state:
            return frame.iloc[0:0].copy(), "no_regional_match", []
        if not in_state.empty:
            return in_state, "same_state_fallback", []
        return frame, "all_available_fallback", []

    @staticmethod
    def _aggregate_mandis(frame: pd.DataFrame) -> list[dict[str, Any]]:
        if frame.empty:
            return []
        work = frame.copy()
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        work = work.dropna(subset=["date", "modal_price"])
        if work.empty:
            return []
        keys = ["state", "district", "market"]
        latest_dates = work.groupby(keys, dropna=False)["date"].max().reset_index(name="latest_date")
        latest = work.merge(latest_dates, on=keys, how="inner")
        latest = latest[latest["date"] == latest["latest_date"]]
        result: list[dict[str, Any]] = []
        for (state, district, market), rows in latest.groupby(keys, dropna=False):
            prices = pd.to_numeric(rows["modal_price"], errors="coerce").dropna()
            if prices.empty:
                continue
            arrivals = pd.to_numeric(rows["arrival_quantity"], errors="coerce").dropna()
            min_values = pd.to_numeric(rows["min_price"], errors="coerce").dropna()
            max_values = pd.to_numeric(rows["max_price"], errors="coerce").dropna()
            quote_details = []
            for row in rows.itertuples():
                quote_price = pd.to_numeric(pd.Series([row.modal_price]), errors="coerce").dropna()
                if quote_price.empty:
                    continue
                quote_details.append({
                    "variety": str(row.variety) if pd.notna(row.variety) else "Not specified",
                    "grade": str(row.grade) if pd.notna(row.grade) else "Not specified",
                    "min_price": round(float(row.min_price), 2) if pd.notna(row.min_price) else None,
                    "max_price": round(float(row.max_price), 2) if pd.notna(row.max_price) else None,
                    "modal_price": round(float(quote_price.iloc[0]), 2),
                    "arrival_quantity": round(float(row.arrival_quantity), 2) if pd.notna(row.arrival_quantity) else None,
                })
            result.append({
                "state": str(state or ""),
                "district": str(district or ""),
                "market": str(market or ""),
                "min_price": round(float(min_values.min()), 2) if not min_values.empty else None,
                "max_price": round(float(max_values.max()), 2) if not max_values.empty else None,
                "modal_price": round(float(prices.median()), 2),
                "modal_price_spread_low": round(float(prices.min()), 2),
                "modal_price_spread_high": round(float(prices.max()), 2),
                "arrival_quantity": round(float(arrivals.sum()), 2) if not arrivals.empty else None,
                "date": pd.Timestamp(rows["date"].max()).date().isoformat(),
                "varieties": sorted({str(v) for v in rows["variety"].dropna().tolist() if str(v).strip()}),
                "grades": sorted({str(v) for v in rows["grade"].dropna().tolist() if str(v).strip()}),
                "quality_quotes": quote_details[:20],
                "records": int(len(rows)),
                "source": ", ".join(sorted({str(v) for v in rows["source"].dropna().tolist()})),
            })
        return sorted(result, key=lambda item: item["modal_price"], reverse=True)

    @staticmethod
    def _daily_series(frame: pd.DataFrame, market: str, district: str | None = None, state: str | None = None) -> pd.DataFrame:
        mask = frame["market"].astype(str).str.casefold() == market.casefold()
        if district:
            mask &= frame["district"].astype(str).str.casefold() == district.casefold()
        if state:
            mask &= frame["state"].astype(str).str.casefold() == state.casefold()
        work = frame[mask].copy()
        empty_columns = ["date", "modal_price", "state", "district", "market", "commodity", "arrival_quantity", "min_price", "max_price", "variety", "grade"]
        if work.empty:
            return pd.DataFrame(columns=empty_columns)
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        for column in ("modal_price", "arrival_quantity", "min_price", "max_price"):
            work[column] = pd.to_numeric(work[column], errors="coerce")
        work = work.dropna(subset=["date", "modal_price"])
        group = work.groupby("date", as_index=False).agg(
            modal_price=("modal_price", "median"),
            arrival_quantity=("arrival_quantity", "sum"),
            min_price=("min_price", "min"),
            max_price=("max_price", "max"),
        )
        latest = work.sort_values("date").iloc[-1]
        group["state"] = latest.get("state", "")
        group["district"] = latest.get("district", "")
        group["market"] = market
        group["commodity"] = latest.get("commodity", "")
        group["variety"] = None
        group["grade"] = None
        group["arrival_quantity"] = group["arrival_quantity"].fillna(0.0)
        group["min_price"] = group["min_price"].fillna(group["modal_price"])
        group["max_price"] = group["max_price"].fillna(group["modal_price"])
        return group.sort_values("date").reset_index(drop=True)

    def _forecast(self, history: pd.DataFrame, horizon: int) -> dict[str, Any]:
        if history.empty:
            return {"available": False, "model": None, "confidence": "none", "history_days": 0, "forecasts": [], "note": "No dated price history is available for a forecast."}
        daily = history.copy().sort_values("date").reset_index(drop=True)
        prices = pd.to_numeric(daily["modal_price"], errors="coerce").dropna().astype(float).to_numpy()
        dates = pd.to_datetime(daily["date"], errors="coerce").dropna()
        count = int(len(prices))
        last_price = float(prices[-1])
        last_date = pd.Timestamp(dates.iloc[-1])
        if count <= 2:
            return {
                "available": True,
                "model": "last-observation baseline",
                "confidence": "very_low",
                "history_days": count,
                "mae": None,
                "direction": "not_established",
                "forecasts": [{"date": (last_date + pd.Timedelta(days=step)).date().isoformat(), "predicted_price": round(last_price, 2), "lower_bound": None, "upper_bound": None} for step in range(1, horizon + 1)],
                "note": "Only one or two distinct trading dates are available. This is a carry-forward reference, not a statistically reliable ML forecast.",
            }
        # Chronological walk-forward comparison: last-observation, 7-point
        # moving average, and a damped linear trend. No random train/test split.
        test_count = min(10, max(2, count // 5))
        start = max(2, count - test_count)
        errors: dict[str, list[float]] = {"last_observation": [], "moving_average_7": [], "damped_linear_trend": []}
        for idx in range(start, count):
            train = prices[:idx]
            actual = prices[idx]
            errors["last_observation"].append(abs(actual - train[-1]))
            errors["moving_average_7"].append(abs(actual - float(np.mean(train[-7:]))))
            lookback = min(14, len(train))
            x = np.arange(lookback, dtype=float)
            slope, intercept = np.polyfit(x, train[-lookback:], 1)
            prediction = intercept + slope * lookback
            prediction = float(np.clip(prediction, train[-1] * 0.8, train[-1] * 1.2))
            errors["damped_linear_trend"].append(abs(actual - prediction))
        maes = {name: float(np.mean(values)) if values else float("inf") for name, values in errors.items()}
        selected = min(maes, key=maes.get)
        mae = maes[selected] if np.isfinite(maes[selected]) else None
        forecasts: list[dict[str, Any]] = []
        working = prices.tolist()
        lookback = min(14, len(working))
        if selected == "damped_linear_trend":
            x = np.arange(lookback, dtype=float)
            slope, intercept = np.polyfit(x, np.asarray(working[-lookback:], dtype=float), 1)
            slope = float(np.clip(slope, -max(last_price * 0.025, 1), max(last_price * 0.025, 1)))
        for step in range(1, horizon + 1):
            if selected == "last_observation":
                prediction = working[-1]
            elif selected == "moving_average_7":
                prediction = float(np.mean(working[-7:]))
            else:
                damp = 0.78 ** (step - 1)
                prediction = intercept + slope * (lookback + (step - 1) * damp)
                prediction = float(np.clip(prediction, last_price * 0.65, last_price * 1.35))
            uncertainty = (mae or 0.0) * (1.0 + (step - 1) * 0.12)
            forecasts.append({
                "date": (last_date + pd.Timedelta(days=step)).date().isoformat(),
                "predicted_price": round(float(prediction), 2),
                "lower_bound": round(max(0.0, float(prediction) - 1.5 * uncertainty), 2) if mae is not None else None,
                "upper_bound": round(float(prediction) + 1.5 * uncertainty, 2) if mae is not None else None,
            })
            working.append(float(prediction))
        # The RF feature set includes up to 30-day lags and the final row has
        # no next-day target. Require enough post-warm-up rows to retain at
        # least 30 training rows after the chronological split.
        if count >= 70:
            try:
                model_result = MarketForecastService().forecast(
                    dataframe=daily,
                    commodity=str(daily["commodity"].iloc[-1]),
                    market=str(daily["market"].iloc[-1]),
                    horizon=horizon,
                )
                model_mae = float(model_result["model_metrics"]["mae"])
                forecasts = [{
                    "date": str(pd.Timestamp(item["date"]).date()),
                    "predicted_price": round(float(item["predicted_price"]), 2),
                    "lower_bound": round(max(0.0, float(item["predicted_price"]) - 1.5 * model_mae), 2),
                    "upper_bound": round(float(item["predicted_price"]) + 1.5 * model_mae, 2),
                } for item in model_result["forecasts"]]
                selected = model_result["model"]
                mae = model_mae
                mape = float(model_result["model_metrics"].get("mape", 100))
                confidence = "high" if mape <= 8 else "medium" if mape <= 12 else "low"
                note = "Model selected by chronological backtesting against naive and moving-average baselines. Validation is on held-out later dates; prediction intervals use validation MAE. Unobserved weather, policy, export, quality and supply shocks are not captured."
            except Exception:
                confidence = "low" if count >= 15 else "very_low"
                note = "The trained model could not pass its fit/backtest checks; using the best small-sample baseline selected by walk-forward MAE."
        else:
            confidence = "low" if count < 15 else "moderate"
            note = "Short-history baseline selected by chronological walk-forward MAE. Forecast is indicative and does not incorporate unobserved policy, weather, export or supply shocks."
        first_pred = forecasts[0]["predicted_price"]
        change = (first_pred - last_price) / last_price * 100 if last_price else 0.0
        direction = "up" if change > 0.75 else "down" if change < -0.75 else "flat"
        return {
            "available": True,
            "model": str(selected),
            "confidence": confidence,
            "history_days": count,
            "mae": round(float(mae), 2) if mae is not None else None,
            "mape": round(float(mape), 2) if count >= 70 and "mape" in locals() else None,
            "direction": direction,
            "forecasts": forecasts,
            "note": note,
        }

    def _build_bundle(self, region: str, commodity: str, horizon: int = 7, force_refresh: bool = False) -> tuple[dict[str, Any], pd.DataFrame]:
        if not str(commodity or "").strip():
            raise ValueError("Commodity is required for market intelligence.")
        if not str(region or "").strip():
            raise ValueError("Enter a city, district or state to find regional mandis.")
        horizon = max(1, min(int(horizon), 30))
        frame, meta = self._get_dataset(region, commodity, force_refresh)
        if frame.empty:
            return ({
                "agent": "market", "available": False, "commodity": commodity,
                "requested_region": region, "source_status": meta["source_status"],
                "source": meta["source"], "warning": meta["warning"] or "No matching regional price observations were found.",
                "mandis": [], "market_tape": [], "history": [], "forecast": [],
            }, frame)
        region_frame, match_type, neighbours = self._regional_slice(frame, meta["state"], meta["district"], region)
        if region_frame.empty and match_type == "no_regional_match":
            return ({
                "agent": "market", "available": False, "commodity": commodity,
                "requested_region": region, "source_status": meta["source_status"],
                "source": meta["source"], "warning": f"No mandi data was found for {region!r}. Add a state or a recognised district so the agent can search the correct neighbouring mandis.",
                "region_match": match_type, "mandis": [], "market_tape": [], "history": [], "forecast": [],
            }, region_frame)
        if region_frame.empty:
            region_frame = frame
        mandis = self._aggregate_mandis(region_frame)
        if not mandis:
            return ({
                "agent": "market", "available": False, "commodity": commodity,
                "requested_region": region, "source_status": meta["source_status"],
                "source": meta["source"], "warning": "No valid positive modal-price observations were found for this crop and region.",
                "mandis": [], "market_tape": [], "history": [], "forecast": [],
            }, region_frame)
        primary_district = meta.get("district")
        today_local = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        for item in mandis:
            item_date = pd.Timestamp(item["date"]).date()
            item_age = max(0, (today_local - item_date).days)
            item["data_age_days"] = item_age
            item["freshness"] = "today" if item_age == 0 else "recent" if item_age <= 3 else "stale"
            item["proximity"] = "requested district" if primary_district and item["district"].casefold() == primary_district.casefold() else ("nearby district" if match_type == "nearby_districts" else "same-state fallback")
        # Prefer recently observed quotes. A stale higher modal price must not
        # be presented as the best price to sell at today.
        fresh_mandis = [item for item in mandis if item["data_age_days"] <= 3]
        ranked_mandis = fresh_mandis if fresh_mandis else mandis
        best = max(ranked_mandis, key=lambda item: (item["modal_price"], item["date"]))
        mandis.sort(key=lambda item: (item is best, item["data_age_days"] <= 3, item["date"], item["modal_price"]), reverse=True)
        history = self._daily_series(region_frame, best["market"], best["district"], best["state"])
        if history.empty:
            history = self._daily_series(frame, best["market"], best["district"], best["state"])
        forecast_meta = self._forecast(history, horizon)
        latest_observed = max(pd.Timestamp(item["date"]).date() for item in mandis)
        age_days = max(0, (today_local - latest_observed).days)
        freshness = "today" if age_days == 0 else "recent" if age_days <= 3 else "stale"
        average_basis = fresh_mandis if fresh_mandis else mandis
        avg_price = float(np.mean([item["modal_price"] for item in average_basis]))
        tape = sorted(mandis, key=lambda item: (item["date"], item["modal_price"]), reverse=True)[:25]
        source_status = meta["source_status"]
        warning = meta["warning"]
        if source_status != "live_api" and not warning:
            warning = "No successful live API refresh is available. Prices shown are saved observations, not verified live quotes."
        if age_days > 3:
            stale_warning = f"Latest available observation is {age_days} days old ({latest_observed.isoformat()}); do not treat it as today's quote."
            warning = f"{warning} {stale_warning}" if warning else stale_warning
        elif age_days > 0:
            recent_warning = f"Latest available observation is {age_days} day(s) old ({latest_observed.isoformat()}); verify with the mandi before dispatch."
            warning = f"{warning} {recent_warning}" if warning else recent_warning
        data = {
            "agent": "market",
            "available": True,
            "commodity": commodity.strip(),
            "price_unit": "INR per quintal",
            "requested_region": region.strip(),
            "resolved_state": meta.get("state"),
            "resolved_district": meta.get("district"),
            "region_match": match_type,
            "nearby_districts_considered": neighbours,
            "source_status": source_status,
            "source": meta["source"],
            "source_url": self.SOURCE_URL,
            "fetched_at": meta["fetched_at"],
            "last_observed_date": latest_observed.isoformat(),
            "data_age_days": age_days,
            "freshness": freshness,
            "api_configured": meta["api_configured"],
            "warning": warning,
            "summary": {
                "best_mandi": best["market"],
                "best_district": best["district"],
                "best_modal_price": best["modal_price"],
                "best_quote_date": best["date"],
                "best_quote_age_days": best["data_age_days"],
                "regional_average_modal_price": round(avg_price, 2),
                "mandi_count": len(mandis),
                "price_basis": "Best regional mandi median from its latest published variety/grade modal-price quotes no older than 3 days; if none qualify, the highest available stale mandi median is labelled. The quote spread is shown where multiple varieties/grades are reported. This is gross price before freight, commission, loading, grading and quality deductions.",
                "best_quote_is_stale": best["data_age_days"] > 3,
            },
            "mandis": mandis[:20],
            "history": [{"date": pd.Timestamp(row.date).date().isoformat(), "modal_price": round(float(row.modal_price), 2)} for row in history.tail(120).itertuples()],
            "forecast": forecast_meta["forecasts"],
            "forecast_meta": {key: value for key, value in forecast_meta.items() if key != "forecasts"},
            "market_tape": tape,
            "tape_kind": "official_daily_price_observations",
            "refresh_interval_seconds": 300,
            "publication_cadence": "daily",
            "streaming_trades_available": False,
            "sources": [
                {"name": "data.gov.in / AGMARKNET", "url": self.SOURCE_URL, "cadence": "daily published mandi prices"},
                {"name": "Maharashtra State Agricultural Marketing Board", "url": self.MSAMB_URL, "cadence": "daily published arrivals and prices"},
                {"name": "e-NAM live dashboard", "url": self.ENAM_URL, "cadence": "public live dashboard for prices, arrivals and trade activity; viewed on the official portal"},
                {"name": "e-NAM trading details", "url": self.ENAM_TRADING_URL, "cadence": "portal trading details; no public API configured in this build"},
            ],
        }
        return data, region_frame

    def get_dashboard(self, region: str, commodity: str = "Onion", horizon: int = 7, force_refresh: bool = False) -> dict[str, Any]:
        result, _ = self._build_bundle(region, commodity, horizon, force_refresh)
        return result

    def get_current_price(self, commodity: str, region: str, force_refresh: bool = False) -> dict[str, Any]:
        dashboard, _ = self._build_bundle(region, commodity, 1, force_refresh)
        if not dashboard.get("available"):
            raise ValueError(dashboard.get("warning") or "No price data is available for this commodity and region.")
        mandis = dashboard.get("mandis", [])
        # Exact named mandi wins. For a district/city query, use the best
        # currently observed modal price from the regional comparison.
        key = self._key(region)
        exact = [item for item in mandis if self._key(item.get("market")) == key]
        chosen = exact[0] if exact else max(mandis, key=lambda item: item["modal_price"])
        age_days = int(chosen.get("data_age_days", dashboard["data_age_days"]))
        is_current = age_days == 0 and dashboard["source_status"] == "live_api"
        freshness = "stale_snapshot" if age_days > 3 else chosen.get("freshness", dashboard["freshness"])
        warning = dashboard.get("warning")
        if not is_current:
            stale_note = "This is not today's live price; verify the current quote with the mandi before sale or dispatch."
            warning = f"{warning} {stale_note}" if warning else stale_note
        return {
            "agent": "market", "commodity": commodity.strip(), "market": region.strip(),
            "current_price": chosen["modal_price"], "latest_observed_price": chosen["modal_price"],
            "price_type": "published modal wholesale price", "last_date": chosen["date"],
            "is_current": is_current,
            "freshness": freshness, "data_age_days": age_days,
            "source": dashboard["source"], "source_status": dashboard["source_status"],
            "fetched_at": dashboard["fetched_at"], "warning": warning,
            "best_available_mandi": chosen["market"], "district": chosen["district"],
            "matched_markets": [item["market"] for item in mandis],
            "market_prices": [{"market": item["market"], "district": item["district"], "modal_price": item["modal_price"], "date": item["date"], "proximity": item["proximity"]} for item in mandis],
            "price_unit": dashboard["price_unit"],
        }

    def get_analysis(self, commodity: str, region: str, horizon: int = 7, **economics: Any) -> dict[str, Any]:
        dashboard, region_frame = self._build_bundle(region, commodity, horizon, False)
        if not dashboard.get("available"):
            raise ValueError(dashboard.get("warning") or "No regional price data is available.")
        best_mandi = dashboard["summary"]["best_mandi"]
        current_price = float(dashboard["summary"]["best_modal_price"])
        forecast = dashboard.get("forecast", [])
        forecast_meta = dashboard.get("forecast_meta", {})
        expected = float(forecast[-1]["predicted_price"]) if forecast else current_price
        change = ((expected - current_price) / current_price * 100) if current_price else 0.0
        prices = [float(point["modal_price"]) for point in dashboard.get("history", [])]
        daily_returns = np.diff(prices) / np.maximum(np.asarray(prices[:-1]), 1) * 100 if len(prices) >= 2 else np.array([])
        volatility = float(np.std(daily_returns)) if len(daily_returns) else 0.0
        if forecast_meta.get("confidence") in {"none", "very_low"} or dashboard["freshness"] == "stale":
            decision = "MONITOR_AND_VERIFY"
            decision_confidence = "low"
            rationale = "The price history or observation freshness is not strong enough for a sell/hold recommendation. Verify today's quote and continue monitoring."
        elif change <= -2.0:
            decision = "SELL_OR_BOOK_A_BUYER"
            decision_confidence = forecast_meta.get("confidence", "low")
            rationale = "The selected forecast indicates a decline from the latest observed modal price; compare net realization and confirm the live auction price before dispatch."
        elif change >= 2.0:
            decision = "HOLD_IF_STORAGE_IS_SAFE"
            decision_confidence = forecast_meta.get("confidence", "low")
            rationale = "The selected forecast indicates a rise; holding only makes sense when storage cost, spoilage and liquidity risk are acceptable."
        else:
            decision = "MONITOR_AND_COMPARE_MANDIS"
            decision_confidence = forecast_meta.get("confidence", "low")
            rationale = "The expected move is small relative to the current quote; compare nearby mandis and net transport cost before deciding."
        transport_cost = float(economics.get("transport_cost") or 0.0)
        storage_cost = float(economics.get("storage_cost") or 0.0)
        nearby_price = economics.get("nearby_market_price")
        nearby_gain = None
        if nearby_price is not None:
            nearby_gain = float(nearby_price) - current_price - transport_cost - storage_cost
        return {
            "agent": "market",
            "commodity": commodity.strip(),
            "market": region.strip(),
            "selected_mandi": best_mandi,
            "context": {"current_price": current_price, "market": best_mandi, "last_date": dashboard["last_observed_date"], "freshness": dashboard["freshness"], "source": dashboard["source"]},
            "market_data": dashboard,
            "risk": {"volatility_pct": round(volatility, 3), "classification": "high" if volatility >= 5 else "moderate" if volatility >= 2 else "low", "based_on_observations": len(prices)},
            "forecast": forecast,
            "model": forecast_meta.get("model"),
            "model_metrics": {"mae": forecast_meta.get("mae"), "mape": forecast_meta.get("mape"), "history_days": forecast_meta.get("history_days"), "confidence": forecast_meta.get("confidence"), "direction": forecast_meta.get("direction")},
            "economics": {"current_price": current_price, "expected_price": round(expected, 2), "expected_change_pct": round(change, 2), "transport_cost": transport_cost, "storage_cost": storage_cost, "nearby_market_price": nearby_price, "nearby_net_advantage": round(nearby_gain, 2) if nearby_gain is not None else None, "cost_warning": "Net realization is unknown until transport, commission, loading, grading and storage costs are entered."},
            "decision": {"decision": decision, "confidence": decision_confidence, "rationale": rationale},
        }
